import requests
from urllib.parse import parse_qs

import odoo
from odoo import http
import json
from odoo.http import request, _logger
from requests.auth import HTTPBasicAuth
import logging
import pytz
import datetime
import threading

class InquiryNotificationController(http.Controller):

    @http.route('/inquiry/get_inquiry_no_request', type='json', auth='user')
    def get_request_price_notifications(self):
        record=[]
        request_price=request.env['request.price'].search([('state','=','draft')])
        if request_price:
            for request_rec in request_price:
                record.append({
                    'id': request_rec.id,
                    'name': request_rec.name,
                })
