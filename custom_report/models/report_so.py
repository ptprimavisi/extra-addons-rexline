from odoo import models, fields, api, _
from odoo.fields import Date
from odoo.exceptions import UserError
from num2words import num2words
import base64
from collections import defaultdict
from datetime import datetime, timedelta,date
import re


class InheritResCompany(models.Model):
    _inherit='res.company'

    sale_logo = fields.Image('Sale Logo', store=True)
    watermark_mrf = fields.Image('Watermark MRF', store=True)
    watermark = fields.Image('Watermark', store=True)
    info = fields.Image('Info', store=True)

    @api.model
    def default_get(self, fields_list):
        res = super(InheritResCompany, self).default_get(fields_list)
        company = self.env.user.company_id
        if company:
            res.update({
                'sale_logo': company.sale_logo,
            })
        return res


class SaleManagerSignature(models.Model):
    _name = 'sale.manager.signature'
    _description = 'Sale Manager Signature'

    employee_id = fields.Many2one('hr.employee', string='Manager')
    image = fields.Image('Image Signature', store=True)

    @api.model
    def default_get(self, fields_list):
        res = super(SaleManagerSignature, self).default_get(fields_list)
        # Cari record signature yang sudah ada
        signature = self.search([], limit=1)
        if signature:
            res.update({
                'employee_id': signature.employee_id.id,
                'image': signature.image,
            })
        return res

    def update_signature(self):
        for rec in self:
            # Buat signature baru
            new_signature = self.env['sale.manager.signature'].create({
                'employee_id': rec.employee_id.id,
                'image': rec.image

            })
            # Cari semua signature lain
            existing_signatures = self.env['sale.manager.signature'].search([('id', '!=', new_signature.id)])
            # Hapus semua signature kecuali signature yang baru saja dibuat
            if existing_signatures:
                for signature in existing_signatures:
                    signature.unlink()



class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    expense_count=fields.Integer(readonly=True)
    customer_ref = fields.Char()

    def get_data(self,recs):
        for rec in recs:
            company = self.env.user.company_id

            company_name = company.partner_id.name or ''
            company_street1 = company.street or ''
            company_street2 = company.partner_id.street2 or ''
            company_street3 = ', '.join(filter(None, [
                rec.company_id.city or '',
                rec.company_id.state_id.name or '',
                rec.company_id.country_id.name or '',
                rec.company_id.zip or ''
            ]))
            company_npwp = company.partner_id.vat or ''
            company_phone = company.partner_id.phone or ''
            company_web = company.website or ''

            partner_name = rec.partner_id.name,
            partner_street1 = rec.partner_id.street or ''
            partner_street2 = rec.partner_id.street2 or ''
            partner_street3 = ', '.join(filter(None, [
                rec.partner_id.city or '',
                rec.partner_id.state_id.name or '',
                rec.partner_id.country_id.name or '',
                rec.partner_id.zip or ''
            ]))

            so_date = rec.date_order.strftime('%d-%m-%Y')
            so_date_due = rec.validity_date.strftime('%d-%m-%Y')
            payment_term = rec.payment_term_id.name or ''
            customer_ref = rec.customer_ref or ''
            so_name = rec.ref_quotation if rec.name == '/' else rec.name
            crm_ids = rec.opportunity_id
            if crm_ids.tag_ids:
                if len(crm_ids.tag_ids)>1:
                    tags = ", ".join(tag.name or '' for tag in crm_ids.tag_ids)
                else:
                    tags = crm_ids.tag_ids.name
                tags_info = tags+', '+so_name
            else:
                tags_info = so_name

            tax_data = defaultdict(lambda: {'percentage': 0, 'tax_amount': 0})

            order_lines=[]
            quotation_lines=[]
            subtotal=0

            for order_line in rec.order_line:
                if order_line.product_id and order_line.product_uom_qty > 0:
                    for tax in order_line.tax_id:
                        # Hitung total pajak untuk setiap baris
                        tax_result = tax.compute_all(
                            order_line.price_unit,
                            rec.currency_id,
                            order_line.product_uom_qty,
                            product=order_line.product_id,
                            partner=rec.partner_id
                        )
                        # Proses hasil pajak
                        for tax_detail in tax_result['taxes']:
                            tax_name = tax.name
                            tax_percentage = tax.amount  # Persentase pajak

                            # Kelompokkan berdasarkan nama pajak dan persentase
                            key = (tax_name, tax_percentage)
                            tax_data[key]['percentage'] = tax_percentage
                            tax_data[key]['tax_amount'] += tax_detail['amount']


                    tax_name=""
                    if order_line.tax_id:
                        tax_name = ", ".join(tax.name for tax in order_line.tax_id)
                    else:
                        tax_name='-'
                    order_lines.append([str(order_line.product_uom_qty)+' '+str(order_line.product_uom.name),order_line.product_id.product_tmpl_id.name,order_line.name,f"{int(order_line.price_unit):,}","0",tax_name,f"{int(order_line.price_subtotal):,}",f"{int(order_line.tax_base):,}"])
                    quotation_lines.append([order_line.name,str(order_line.product_uom_qty)+' '+str(order_line.product_uom.name),'0',f"{int(order_line.price_unit):,}",f"{int(order_line.price_subtotal):,}",f"{int(order_line.tax_base):,}"])
                    subtotal+=order_line.price_subtotal

            # Format hasil
            taxes = [{'name': key[0], 'percentage': key[1], 'amount': f"{int(values['tax_amount']):,}"}
                    for key, values in tax_data.items()]

            total_tax_base = f"{int(rec.amount_tax_base):,}"

            subtotal = f"{int(subtotal):,}"
            balance_due = f"{int(rec.amount_total):,}"
            balance_due_in_word =num2words(rec.amount_total, lang='en').upper()

            company_logo=self.env.company.logo
            logo = (
                f"data:image/png;base64,{self.env.company.sale_logo.decode('utf-8')}"
                if self.env.company.sale_logo
                else None
            )

            # Get T&C
            so_tnc = rec.note or ''
            bank_name = rec.bank_name or ''
            bank_branch = rec.bank_branch or ''
            bank_number = rec.bank_number or ''
            bank_account_name = rec.bank_account_name or ''

            # Get Manager Signature
            signature = self.env['sale.manager.signature'].search([],limit=1)
            signature_name = signature.employee_id.name
            signature_image = (
                f"data:image/png;base64,{signature.image.decode('utf-8')}"
                if signature and signature.image
                else None
            )
            # raise UserError(f'{signature_image}')

            report_data = {
                    'doc_ids': self.ids,
                    'doc_model': 'sale.order',
                    'company_name': company_name,
                    'company_street1':company_street1,
                    'company_street2':company_street2,
                    'company_street3':company_street3,
                    'company_phone':company_phone,
                    'company_npwp':company_npwp,
                    'company_web':company_web,
                    'partner_name':partner_name[0],
                    'partner_street1':partner_street1,
                    'partner_street2':partner_street2,
                    'partner_street3':partner_street3,
                    'so_name':so_name,
                    'so_date':so_date,
                    'so_date_due':so_date_due,
                    'so_term': str(payment_term),
                    'customer_ref': str(customer_ref),
                    'so_tnc':so_tnc,
                    'balance_due':balance_due,
                    'subtotal':subtotal,
                    'tags_info':tags_info,
                    'taxes':taxes,
                    'order_lines':order_lines,
                    'quotation_lines':quotation_lines,
                    'company_logo':company_logo,
                    'signature_name':signature_name,
                    'signature_image':signature_image,
                    'logo':logo,
                    'balance_due_in_word':balance_due_in_word,
                    'total_tax_base':total_tax_base,
                    'bank_name': bank_name,
                    'bank_branch': bank_branch,
                    'bank_number': bank_number,
                    'bank_account_name': bank_account_name,
                }
            return report_data

    def action_print_custom_so(self):
        for recs in self:
            report_data=self.get_data(recs)
            return self.env.ref('custom_report.action_report_so').with_context(
                name=recs.name, paperformat=4, landscape=False).report_action([], data=report_data, config=False)

    def action_print_custom_quotation(self):
        for recs in self:
            report_data=self.get_data(recs)
            return self.env.ref('custom_report.action_report_quotation').with_context(
                paperformat=4, landscape=False).report_action(self, data=report_data, config=False)

    # def action_print_so(self):
    #     for line in self:
    #         pass


