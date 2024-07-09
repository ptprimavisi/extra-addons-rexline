from abc import ABC

from odoo import models, api, fields
from datetime import datetime
from odoo.exceptions import UserError


class TableUsers(models.Model):
    _name = 'table.user'

    namalengkap = fields.Char()
    username = fields.Char()
    password = fields.Char()
    status = fields.Char()