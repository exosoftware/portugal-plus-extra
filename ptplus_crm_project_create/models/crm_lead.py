from odoo import models


class Lead(models.Model):
    _inherit = "crm.lead"

    def action_open_crm_project(self):
        self.ensure_one()
        if self.project_id:
            self.project_id.crm_id = self.id
            return {
                "type": "ir.actions.act_window",
                "res_model": "project.project",
                "view_mode": "form",
                "res_id": self.project_id.id,
                "target": "current",
                "context": {"default_crm_id": self.id},
            }

    def action_view_crm_project_tasks(self):
        self.ensure_one()
        if self.project_id and self.project_id.tasks:
            return {
                "name": self.project_id.name,
                "type": "ir.actions.act_window",
                "res_model": "project.task",
                "view_mode": "kanban,list,form",
                "domain": [("project_id", "=", self.project_id.id)],
                "context": {"default_project_id": self.project_id.id},
            }
