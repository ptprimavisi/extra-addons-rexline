import json
import logging

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.service import security
from odoo.tools import ustr
from odoo.tools.translate import _
# from .utils import ensure_db, _get_login_redirect_url, is_user_internal


class ApiTest(http.Controller):
    @http.route('/api/get_user',type="json", auth="none",csrf=False)
    def get_user(self, **kwargs):
        request.session.db = 'rexline'
        request.uid = odoo.SUPERUSER_ID
        data = request.params
        return {
            'message': 'success',
            'data': {
                'name': 'nhe'
            }
        }
