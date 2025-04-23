from odoo import models, api, fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class MultiApproval(models.Model):
    _inherit = 'multi.approval'

    # partner_id = fields.Many2one('res.partner', compute="_compute_partner", store=True)
    # sale = fields.Char(compute="_compute_sale", store=True)
    #
    # def _compute_partner(self):
    #     for line in self:
    #         line.partner_id = False
    #         model = str(line.origin_ref)
    #         if model:
    #             model_name = model.split(",")[0]
    #             model_id = model.split(",")[1]
    #             source = self.env[model_name].search([('id', '=', model_id)])
    #             if source:
    #                 if hasattr(source, 'partner_id'):
    #                     if source.partner_id:
    #                         line.partner_id = source.partner_id.id
    #
    # def _compute_sale(self):
    #     for line in self:
    #         line.sale = False
    #         model = str(line.origin_ref)
    #         if model:
    #             model_name = model.split(",")[0]
    #             model_id = model.split(",")[1]
    #             if model_name == 'request.price':
    #                 price_req = self.env['request.price'].search([('id', '=', model_id)])
    #                 if price_req:
    #                     if price_req.inquiry_id:
    #                         if price_req.inquiry_id:
