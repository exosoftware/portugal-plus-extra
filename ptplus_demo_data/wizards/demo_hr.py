##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
from odoo import _, fields, models


class PtplusDemoDataWizard(models.TransientModel):
    _inherit = "ptplus.demo.data.wizard"

    def _demo_generate_payroll(self, company, partner):
        log = []
        employee = self._demo_get_or_create_employee_roster(company)[:1]

        structure_type = self.env["hr.payroll.structure.type"].search(
            [("name", "=", _("Salário Mensal PT"))], limit=1
        )
        if not structure_type:
            structure_type = self.env["hr.payroll.structure.type"].create(
                {
                    "name": _("Salário Mensal PT"),
                    "country_id": company.country_id.id,
                }
            )

        structure = self.env["hr.payroll.structure"].search(
            [("type_id", "=", structure_type.id)], limit=1
        )
        if not structure:
            structure = self.env["hr.payroll.structure"].create(
                {
                    "name": _("Processamento Mensal"),
                    "type_id": structure_type.id,
                }
            )
            structure_type.default_struct_id = structure.id

        version = self.env["hr.version"].search(
            [("employee_id", "=", employee.id)], limit=1
        )
        version.write(
            {
                "wage": 1500.0,
                "structure_type_id": structure_type.id,
            }
        )

        date_from = fields.Date.context_today(self).replace(day=1)
        payslip = self.env["hr.payslip"].create(
            {
                "name": _("Recibo de Vencimento - %s") % employee.name,
                "employee_id": employee.id,
                "date_from": date_from,
                "struct_id": structure.id,
            }
        )
        payslip.compute_sheet()
        log.append(_("Recibo de vencimento criado para %s") % employee.name)
        return log
