##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class MultiApproval(models.Model):
    _inherit = "multi.approval"

    origin_ref = fields.Reference(string="Origin", selection="_selection_target_model")

    @api.model
    def _selection_target_model(self):
        models = self.env["ir.model"].search([])
        return [(model.model, model.name) for model in models]

    def update_source_obj(self, obj, result="approved", log_msg=""):
        if not obj:
            return False
        obj.write(
            {
                "x_review_result": result,
            }
        )
        if log_msg and hasattr(obj, "message_post"):
            obj.message_post(body=log_msg)

    def finalize_related_document(self):
        log_msg = _("{} has approved this document !").format(self.env.user.name)
        self.update_source_obj(self.origin_ref, log_msg=log_msg)

    def get_next_move(self):
        if not self.type_id.model_id or not self.type_id.next_move_ids:
            return None
        types = self.env["multi.approval.type"]._get_types(self.type_id.model_id)
        if not types:
            return None
        types = types & self.type_id.next_move_ids
        approval_type = self.env["multi.approval.type"].filter_type(
            types, self.type_id.model_id, self.origin_ref.id
        )
        return approval_type

    def set_approved(self, send_mail=True):
        # customized code
        # 1. Write a log on the source document
        # 2. Call the callback action when approved
        # Note: always update the x_has_approved first !
        if not self.origin_ref:
            return super().set_approved(send_mail)
        res = self.type_id.run(self, self.origin_ref)
        next_move = self.get_next_move()
        if next_move and next_move.line_ids:
            send_mail = False
            new_approval = self.sudo().copy({"type_id": next_move.id})
            new_approval.action_submit()
        else:
            self.finalize_related_document()
        super().set_approved(send_mail)
        if res:
            return res

    def set_refused(self, reason="", send_mail=True):
        super().set_refused(reason, send_mail)

        # customized code
        # 1. Write a log on the source document
        # 2. Call the callback action when refused
        # Note: always update the x_has_approved first !
        if not self.origin_ref:
            return False
        log_msg = _(
            "{name} has refused this document due to this reason: {reason}"
        ).format(name=self.env.user.name, reason=reason)
        self.update_source_obj(self.origin_ref, "refused", log_msg)
        res = self.type_id.run(self, self.origin_ref, "refuse")
        if res:
            return res

    @api.model
    def open_request(self):
        ctx = self._context
        model_name = ctx.get("active_model")
        res_id = ctx.get("active_id")
        origin_ref = f"{model_name},{res_id}"
        return {
            "name": "My Requests",
            "type": "ir.actions.act_window",
            "res_model": "multi.approval",
            "view_type": "list",
            "view_mode": "list,form",
            "target": "current",
            "domain": [("origin_ref", "=", origin_ref)],
        }
