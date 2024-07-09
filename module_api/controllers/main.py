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

class ApiController(http.Controller):
    @http.route('/api/get_users', type='json', methods=['GET'], auth="none")
    def get_user(self, **kwargs):
        db = 'rexline'
        uid = request.session.authenticate(db, 'admin', 'admin123')
        request.session.db = db
        request.session.uid = odoo.SUPERUSER_ID
        userid = kwargs.get('userid')
        param = request.params
        user_id = request.httprequest.args.get('userid')

        if user_id:
            list = []
            if user_id == 'all':
                users = request.env['tbl.users'].search([])
            else:
                users = request.env['tbl.users'].search([('id', '=', user_id)])
            for line in users:
                list.append({
                    'namalengkap': line.namalengkap,
                    'username': line.username,
                    'password': line.password,
                    'password': line.status
                })
            data = {
                'message': 'success',
                'data': list
            }
        else:
            data = {
                'message': 'Missing params of userid',
                'data': {}
            }
        return data

    @http.route('/api/create_user', type='json', methods=['POST'], auth="none")
    def insert_user(self):
        db = 'rexline'
        uid = request.session.authenticate(db, 'admin', 'admin123')
        request.session.db = db
        request.session.uid = odoo.SUPERUSER_ID
        param = request.params
        if param.get('namalengkap') and param.get('username') and param.get('password') and param.get('status'):
            datas = request.env['tbl.users'].create({
                "namalengkap": param['namalengkap'],
                "username": param['username'],
                "password": param['password'],
                "status": param['status'],
            })
            if datas:
                data = {
                    "message": 'Success',
                    'ID': datas.id
                }
        else:
            data =  {
                "message": 'Misiing body'
            }
        return data

    @http.route('/api/delete_users', type='json', methods=['GET'], auth="none")
    def delete_user(self, **kwargs):
        db = 'rexline'
        uid = request.session.authenticate(db, 'admin', 'admin123')
        request.session.db = db
        request.session.uid = odoo.SUPERUSER_ID
        user_id = request.httprequest.args.get('userid')

        if user_id:
            users = request.env['tbl.users'].search([('id', '=', user_id)])
            if users:
                users.unlink()
            data = {
                'message': 'success'
            }
        else:
            data = {
                'message': 'missing params',
            }
        return data
