from odoo import models, fields, api, _
from odoo.fields import Date
from odoo.exceptions import UserError
import base64
from datetime import datetime, timedelta,date
import re

class SaleDirekturSignature(models.Model):
    _name = 'sale.direktur.signature'
    _description = 'Sale Direktur Signature'

    employee_id = fields.Many2one('hr.employee', string='Direktur')
    image = fields.Image('Image Signature', store=True)

    @api.model
    def default_get(self, fields_list):
        res = super(SaleDirekturSignature, self).default_get(fields_list)
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
            new_signature = self.env['sale.direktur.signature'].create({
                'employee_id': rec.employee_id.id,
                'image': rec.image
                
            })
            # Cari semua signature lain
            existing_signatures = self.env['sale.direktur.signature'].search([('id', '!=', new_signature.id)])
            # Hapus semua signature kecuali signature yang baru saja dibuat
            if existing_signatures:
                for signature in existing_signatures:
                    signature.unlink()

class InheritInvoice(models.Model):
    _inherit = 'account.move'

    def action_print_custom(self):
        for rec in self:
            company = self.env.user.company_id

            company_name = company.partner_id.name or ''
            company_street1 = company.partner_id.street or ''
            company_street2 = company.partner_id.street2 or ''
            company_street3 = ', '.join(filter(None, [
                rec.company_id.city or '',
                rec.company_id.state_id.name or '',
                rec.company_id.country_id.name or '',
                rec.company_id.zip or ''
            ]))
            company_npwp = company.partner_id.vat or ''
            company_phone = company.partner_id.phone or ''
            company_web = company.partner_id.website or ''

            partner_name = rec.partner_id.name,
            partner_street1 = rec.partner_id.street or ''
            partner_street2 = rec.partner_id.street2 or ''
            partner_street3 = ', '.join(filter(None, [
                rec.partner_id.city or '',
                rec.partner_id.state_id.name or '',
                rec.partner_id.country_id.name or '',
                rec.partner_id.zip or ''
            ]))
            
            invoice_name = rec.name
            invoice_date = rec.invoice_date.strftime('%d-%m-%Y') if rec.invoice_date else ''
            invoice_date_due = rec.invoice_date_due.strftime('%d-%m-%Y') if rec.invoice_date_due else ''
            
            balance_due = f"{rec.amount_total:,}"
            round_balance_due = f"{int(rec.amount_total):,.0f}"+'.00'
            rounded = round(rec.amount_total - int(rec.amount_total), 2)

            so_ids = rec.line_ids.sale_line_ids.order_id
            so_name = so_ids.ref_quotation if so_ids.name == '/' else so_ids.name
            so_name = so_name or ''
            crm_ids = so_ids.opportunity_id
            if crm_ids.tag_ids:
                if len(crm_ids.tag_ids)>1:
                    tags = ", ".join(tag.name or '' for tag in crm_ids.tag_ids)
                else:
                    tags = "".join(tag.name or '' for tag in crm_ids.tag_ids)
                tags_info = tags+', '+so_name
            else:
                tags_info = so_name
            # raise UserError(tags_info)

            taxes=[]

            query="""
                SELECT 
                    tax.id AS tax, 
                    tax.invoice_label as tax_label,
                    tax.amount as percentage,
                    COALESCE(abs(SUM(aml.balance)), 0) AS tax_amount
                FROM account_move_line aml
                join account_tax tax on aml.tax_line_id=tax.id
                WHERE 
                    aml.move_id = """+str(rec.id)+"""
                    AND aml.display_type = 'tax'
                GROUP BY 
                    tax.id,tax.invoice_label,tax.amount;
            """
            self.env.cr.execute(query)
            query_vals = self.env.cr.dictfetchall()
            if query_vals:
                for line in query_vals:
                    tax_name=self.env['account.tax'].search([('id','=',line['tax'])]).name
                    taxes.append({
                        'name':tax_name,
                        'percentage':12 if '12' in tax_name else line['percentage'],
                        'amount':f"{line['tax_amount']:,.2f}"})

            product_line=[]
            move_lines = self.env['account.move.line'].search([('move_id','=',rec.id),('product_id','!=',False)])
            subtotal=0
            if move_lines:
                for lines in move_lines:
                    tax_name=''
                    if lines.tax_ids:
                        tax_name = ", ".join(tax.name for tax in lines.tax_ids)
                    else:
                        tax_name='-'
                    product_line.append([lines.name,str(lines.quantity)+' '+str(lines.product_uom_id.name),f"{round(lines.price_unit,2):,}",f"{round(lines.discount,2):,}",tax_name,f"{round(lines.price_subtotal,2):,}",f"{round(lines.tax_base,2):,}"])
                    subtotal+=lines.price_subtotal
            subtotal = f"{round(subtotal,2):,}"

            total_tax_base = f"{round(rec.amount_tax_base,2):,}"

            # Get Direktur Signature
            signature = self.env['sale.direktur.signature'].search([],limit=1)
            signature_name = signature.employee_id.name
            signature_image = (
                f"data:image/png;base64,{signature.image.decode('utf-8')}"
                if signature and signature.image
                else None
            )

            logo = self.env.company.sale_logo
            logo = (
                f"data:image/png;base64,{self.env.company.sale_logo.decode('utf-8')}"
                if self.env.company.sale_logo
                else None
            )

            invoice_tnc = rec.narration or ''

            # Hitung jumlah baris secara dinamis
            total_rows = len(taxes) + 5  # 5 adalah jumlah baris tetap di luar 'taxes'
            
            report_data = {
                    'doc_ids': self.ids,
                    'doc_model': 'account.move',
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
                    'invoice_name':invoice_name,
                    'invoice_date':invoice_date,
                    'invoice_date_due':invoice_date_due,
                    'balance_due':balance_due,
                    'round_balance_due':round_balance_due,
                    'rounded':rounded,
                    'subtotal':subtotal,
                    'tags_info':tags_info,
                    'taxes':taxes,
                    'product_line':product_line,
                    'signature_name':signature_name,
                    'signature_image':signature_image,
                    'logo':logo,
                    'invoice_tnc':invoice_tnc,
                    'total_tax_base':total_tax_base,
                    'total_rows':total_rows
                }
            return self.env.ref('custom_report.action_report_invoice').with_context(
                paperformat=4, landscape=False).report_action(self, data=report_data)