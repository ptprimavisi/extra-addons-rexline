from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime
from datetime import date


# class InheritHrDepartment(models.Model):
#     _inherit='hr.department'

#     code = fields.Char()


# class InheritResUsers(models.Model):
#     _inherit='res.users'

    # is_it = fields.Boolean()


class InheritPurchaseOrderLine(models.Model):
    _inherit='purchase.order.line'

    is_generate_asset=fields.Boolean()


class InheritPurchaseOrder(models.Model):
    _inherit='purchase.order'

    is_generate_asset=fields.Boolean(compute='compute_generate')

    @api.depends('order_line')
    def compute_generate(self):
        for rec in self:
            user=self.env.user
            # if user.is_it:
            #     # Check if any line has qty_received < 1 and if all lines have is_generate_asset == True
            #     if any(line.qty_received < 1 for line in rec.order_line):
            #         rec.is_generate_asset = True  # If any line has qty_received < 1, don't generate asset
            #     elif all(line.is_generate_asset == True for line in rec.order_line):
            #         rec.is_generate_asset = True  # If all lines are marked to generate asset, set True
            #     else:
            #         rec.is_generate_asset = False  # Default case, if neither condition is met
            # else:
            #     rec.is_generate_asset = True
            # Check if any line has qty_received < 1 and if all lines have is_generate_asset == True
            if any(line.qty_received < 1 for line in rec.order_line):
                rec.is_generate_asset = True  # If any line has qty_received < 1, don't generate asset
            elif all(line.is_generate_asset == True for line in rec.order_line):
                rec.is_generate_asset = True  # If all lines are marked to generate asset, set True
            else:
                rec.is_generate_asset = False  # Default case, if neither condition is met

    def action_generate(self):
        for rec in self:
            for product in rec.order_line:
                if all(product.is_generate_asset for line in rec.order_line):
                    raise UserError('All products have already been added to the Asset Management master.')
                if product.is_generate_asset==False:
                    if product.product_id.product_tmpl_id.type=='product':
                        asset_type='storable'
                    else:
                        asset_type='consumable'
                    vals={
                        'product_name':product.product_id.product_tmpl_id.name,
                        'asset_type':asset_type,
                        'qty':product.qty_received,
                        'uom_id':product.product_uom.id,
                        'value':product.qty_received*product.price_unit,
                        'purchase_id':product.order_id.id,
                        'purchase_date':product.order_id.date_approve.date(),
                        'delivered_date':product.order_id.effective_date.date(),
                        'status':'active'
                    }
                    manajemen_assets=self.env['manajemen.assets'].create(vals)
                    product.write({'is_generate_asset':True})
            assets=self.env['manajemen.assets'].search([('purchase_id','=',rec.id)])
            if assets:
                action = {
                    'name': 'Manajemen Assets',
                    'type': 'ir.actions.act_window',
                    'res_model': 'manajemen.assets',
                    'view_mode': 'tree,form',
                    'domain': [('purchase_id', '=', rec.id)],
                    'target': 'current',
                }
                return action
            

class ManajemenAssets(models.Model):
    _name ='manajemen.assets'
    _inherit = ['mail.thread']

    name = fields.Char(string='Inventory Number')
    asset_type = fields.Selection([
        ('storable', 'Hardware'),
        ('consumable', 'Software')], string='Asset Type')
    product_name=fields.Char(string='Product')
    qty=fields.Float('Quantity')
    uom_id=fields.Many2one('uom.uom')
    value=fields.Float()
    purchase_id=fields.Many2one('purchase.order')
    mac_address=fields.Char()
    serial_number=fields.Char()
    brand=fields.Char()
    tipe=fields.Char()
    prepetual=fields.Date()
    # purchase_date=fields.Date(compute="_compute_purchase_date",store=True)
    purchase_date=fields.Date()
    spesification=fields.Char()
    pic=fields.Many2one('hr.employee',string='PIC')
    location=fields.Char()
    designation=fields.Char()
    department=fields.Many2one('hr.department')
    head_department= fields.Many2one('hr.employee')
    delivered_date=fields.Date()
    returned_date=fields.Date()
    transfer_date=fields.Date()
    expired_date=fields.Date()
    admin_login=fields.Char()
    portal_admin=fields.Char()
    contact_person=fields.Char()
    license_number=fields.Integer(string='Number of License')
    remarks=fields.Text(string='Remarks')
    validity_days=fields.Integer(string='Validity in Days')
    current_date=fields.Date(default=fields.Date.context_today, compute="_compute_current_date")
    usage_month=fields.Float(string='Periode of Usage (Month)', compute="_compute_usage_month")
    usage_day=fields.Integer(string='Number of Days in Usage', compute="_compute_usage_day")
    depreciation=fields.Float(string='Depreciation', compute="_compute_depreciation")
    current_value=fields.Float(string='Current Value', compute="_compute_current_value")
    upgrade_ssd = fields.Boolean(string='Upgrade SSD')
    spec_type = fields.Selection([
        ('std', 'STD'), 
        ('hgh', 'HGH')], string='Spec Type')
    status = fields.Selection([
        ('active', 'Active'), 
        ('inactive', 'Inactive')], string='Status')


    def write(self, vals):
        for record in self:
            field_labels = []
            log_message = ""
            user_name = self.env.user.name

            # Iterate over the keys in vals (these are field names)
            for field_name, field_value in vals.items():
                # Get the field label using the model's fields_get method
                field_label = record._fields[field_name].string

                # If the field is a Many2one relation (i.e., an ID field pointing to another model)
                field = record._fields[field_name]
                if field.type == 'many2one' and field_value:
                    related_record = self.env[field.comodel_name].browse(field_value)
                    field_value = related_record.name  # Get the name of the related record

                # Add the field label and its value to the message
                field_labels.append(f"{field_label}: {field_value}")
                log_message += f"\n{field_label} → {field_value}"  # Use plain text for logging

            # Check if the log message has changed and format the user_name correctly
            if log_message:
                record.message_post(
                    body=f"Record updated by {user_name}.\nChanges:\n{log_message}",
                    subject="Record Updated",
                    message_type='notification',
                    subtype_xmlid='mail.mt_note'  # To ensure it appears correctly in chatter
                )

            result = super(ManajemenAssets, self).write(vals)
        return result


    def action_update_today(self):
        for rec in self:
            rec.current_date = fields.Date.today()
            rec._compute_usage_day()

    @api.depends('delivered_date','returned_date')
    def _compute_usage_month(self):
        for rec in self:
            rec.usage_month=0
            if rec.delivered_date and rec.returned_date:
                delivered_date = fields.Date.from_string(rec.delivered_date)
                returned_date = fields.Date.from_string(rec.returned_date)
                difference_in_days = (returned_date - delivered_date).days
                rec.usage_month = difference_in_days / (365 / 12)

    # @api.depends('purchase_id')
    # def _compute_purchase_date(self):
    #     for rec in self:
    #         if rec.purchase_id:
    #             rec.purchase_date=rec.purchase_id.date_approve.date()

    def _compute_current_date(self):
        for record in self:
            record.current_date = fields.Date.context_today(record)

    @api.model
    def update_usage_day(self):
        records = self.search([])
        for record in records:
            record._compute_usage_day()

    @api.depends('purchase_date')
    def _compute_usage_day(self):
        for rec in self:
            rec.usage_day=0
            if rec.purchase_date:
                purchase_date = fields.Date.from_string(rec.purchase_date)
                today = date.today()
                rec.usage_day = (today - purchase_date).days

    @api.depends('value','usage_day','validity_days','current_date')
    def _compute_depreciation(self):
        for rec in self:
            rec.depreciation=0
            if rec.value and rec.usage_day and rec.validity_days:
                rec.depreciation=(rec.value/rec.validity_days)*rec.usage_day
    
    @api.depends('value','depreciation')
    def _compute_current_value(self):
        for rec in self:
            rec.current_value=0
            if rec.value and rec.depreciation:
                rec.current_value=rec.value-rec.depreciation
                

    



