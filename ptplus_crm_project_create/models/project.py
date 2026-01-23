from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    crm_id = fields.Many2one("crm.lead")

    def action_open_crm_lead(self):
        self.ensure_one()
        if self.crm_id:
            return {
                "name": self.crm_id.name,
                "type": "ir.actions.act_window",
                "res_model": "crm.lead",
                "view_mode": "form",
                "res_id": self.crm_id.id,
                "target": "current",
            }
