##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
from odoo import _, models
from odoo.fields import Command


class PtplusDemoDataWizard(models.TransientModel):
    _inherit = "ptplus.demo.data.wizard"

    def _demo_generate_crm(self, company, partner):
        log = []
        team = self.env.ref(
            "sales_team.team_sales_department", raise_if_not_found=False
        )
        stages = {
            "new": self.env.ref("crm.stage_lead1", raise_if_not_found=False),
            "qualified": self.env.ref("crm.stage_lead2", raise_if_not_found=False),
            "proposition": self.env.ref("crm.stage_lead3", raise_if_not_found=False),
            "won": self.env.ref("crm.stage_lead4", raise_if_not_found=False),
        }
        opportunities = [
            (_("Projeto de Engenharia - Edifício Sede"), 45000.0, stages["new"], 20),
            (
                _("Fiscalização de Obra - Parque Industrial"),
                28000.0,
                stages["qualified"],
                40,
            ),
            (
                _("Consultoria Técnica - Ampliação de Fábrica"),
                15000.0,
                stages["proposition"],
                70,
            ),
            (_("Licenciamento - Loteamento Urbano"), 9000.0, stages["won"], 100),
        ]
        for name, revenue, stage, probability in opportunities:
            lead = self.env["crm.lead"].create(
                {
                    "name": name,
                    "type": "opportunity",
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "expected_revenue": revenue,
                    "probability": probability,
                    "stage_id": stage.id if stage else False,
                    "team_id": team.id if team else False,
                    "user_id": self.env.uid,
                }
            )
            log.append(_("Oportunidade CRM criada: %s") % lead.name)
        return log

    def _demo_generate_voip(self, company, partner):
        log = []
        calls = [
            ("outgoing", "terminated"),
            ("incoming", "terminated"),
            ("incoming", "missed"),
        ]
        for direction, state in calls:
            call = self.env["voip.call"].create(
                {
                    "phone_number": partner.phone or "+351210000000",
                    "partner_id": partner.id,
                    "user_id": self.env.uid,
                    "direction": direction,
                    "state": state,
                }
            )
            log.append(
                _("Chamada VoIP registada: %s (%s)") % (call.phone_number, state)
            )
        return log

    def _demo_generate_sales(self, company, partner):
        """Quotation template with lines, applied to a new quotation."""
        log = []
        service = self._demo_get_or_create_product(
            company, _("Serviços de Consultoria Técnica"), 850.0, False
        )
        material = self._demo_get_or_create_product(
            company, _("Materiais de Construção"), 120.0, True
        )
        template = self.env["sale.order.template"].create(
            {
                "name": _("Proposta Padrão - Engenharia Civil"),
                "company_id": company.id,
                "sale_order_template_line_ids": [
                    Command.create(
                        {
                            "product_id": service.product_variant_id.id,
                            "product_uom_qty": 1,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": material.product_variant_id.id,
                            "product_uom_qty": 20,
                        }
                    ),
                ],
            }
        )
        log.append(_("Modelo de orçamento criado: %s") % template.name)

        quotation = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                "sale_order_template_id": template.id,
                "order_line": [
                    Command.create(line._prepare_order_line_values())
                    for line in template.sale_order_template_line_ids
                ],
            }
        )
        quotation.pt_issue()
        log.append(
            _("Orçamento criado a partir do modelo '%s': %s")
            % (template.name, quotation.name)
        )
        return log
