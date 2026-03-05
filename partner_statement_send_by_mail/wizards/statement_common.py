from odoo import models


class StatementCommonWizard(models.AbstractModel):
    _inherit = "statement.common.wizard"

    def button_send_mail(self):
        self.ensure_one()
        return self._send_mail()

    def _send_mail(self):
        raise NotImplementedError
