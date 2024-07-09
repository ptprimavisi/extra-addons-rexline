import requests
from urllib.parse import parse_qs

import odoo
from odoo import http
import json
from odoo.http import request, _logger
from requests.auth import HTTPBasicAuth
import logging
import threading


class SaleOrderController(http.Controller):
    @http.route('/sale/get_inquiry', type='json', auth='public', website=True)
    def call_method(self, **kwargs):
        # Call the method of the Odoo model
        result = request.env['request.price'].search([('state','=', 'draft')])
        a = []
        uid = request.env.uid
        users = request.env['res.users'].browse(uid)
        if users.is_purchase:
            if result:
                for line in result:
                    a.append({
                        'id': int(line.id),
                        'name': str(line.inquiry_id.name)
                    })

        #
        # # Format the result as JSON
        # result_json = json.dumps(result)

        return a


