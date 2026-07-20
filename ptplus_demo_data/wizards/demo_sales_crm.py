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
            (_("Proposta Comercial - Novo Cliente"), 12000.0, stages["new"], 20),
            (_("Renovação de Contrato Anual"), 8000.0, stages["qualified"], 40),
            (_("Serviço de Consultoria - Fase 2"), 15000.0, stages["proposition"], 70),
            (_("Parceria Estratégica"), 6000.0, stages["won"], 100),
        ]
        if self._demo_is_civil_engineering():
            opportunities += [
                (
                    _("Projeto de Engenharia - Edifício Sede"),
                    45000.0,
                    stages["new"],
                    20,
                ),
                (
                    _("Fiscalização de Obra - Parque Industrial"),
                    28000.0,
                    stages["qualified"],
                    40,
                ),
                (
                    _("Licenciamento - Loteamento Urbano"),
                    9000.0,
                    stages["proposition"],
                    60,
                ),
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
            ("outgoing", "terminated", True),
            ("incoming", "terminated", True),
            ("incoming", "missed", False),
            ("outgoing", "terminated", True),
            ("incoming", "rejected", False),
        ]
        transcripts = iter(
            [
                _(
                    "Resumo da chamada: cliente confirmou interesse na proposta "
                    "enviada e pediu esclarecimentos sobre o prazo de entrega."
                ),
                _(
                    "Resumo da chamada: agendada visita técnica para a próxima "
                    "semana; cliente sem questões adicionais."
                ),
                _(
                    "Resumo da chamada: cliente confirmou receção da fatura e "
                    "indicou que o pagamento será efetuado dentro do prazo."
                ),
            ]
        )
        transcript_count = 0
        for direction, state, with_transcript in calls:
            call = self.env["voip.call"].create(
                {
                    "phone_number": partner.phone or "+351210000000",
                    "partner_id": partner.id,
                    "user_id": self.env.uid,
                    "direction": direction,
                    "state": state,
                }
            )
            if with_transcript:
                # voip.call has no dedicated transcript field; it inherits
                # mail.thread (via mail.thread.main.attachment), so a chatter
                # note is the standard way to attach one.
                call.message_post(body=next(transcripts))
                transcript_count += 1
            log.append(
                _("Chamada VoIP registada: %s (%s)") % (call.phone_number, state)
            )
        log.append(_("%s chamada(s) com transcrição/resumo") % transcript_count)
        return log

    def _demo_get_or_create_project_templates(self, company):
        """3 project.project records flagged as reusable templates.

        A "project template" is just a regular project.project with
        is_template=True (project/models/project_project.py) -- referencing
        one from a product's project_template_id makes sale_project copy it
        into a real project when that product's line gets confirmed.
        """
        names = [
            _("Modelo - Consultoria Rápida"),
            _("Modelo - Implementação Standard"),
            _("Modelo - Projeto Completo"),
        ]
        templates = self.env["project.project"]
        for name in names:
            template = self.env["project.project"].search(
                [("name", "=", name), ("company_id", "=", company.id)], limit=1
            )
            if not template:
                template = self.env["project.project"].create(
                    {"name": name, "company_id": company.id, "is_template": True}
                )
            templates |= template
        return templates

    def _demo_get_or_create_service_product(
        self,
        company,
        name,
        list_price,
        service_tracking,
        project_id=False,
        project_template_id=False,
    ):
        product = self.env["product.template"].search(
            [("name", "=", name), ("company_id", "in", [company.id, False])], limit=1
        )
        if product:
            return product
        return self.env["product.template"].create(
            {
                "name": name,
                "type": "service",
                "list_price": list_price,
                "sale_ok": True,
                "purchase_ok": False,
                "company_id": company.id,
                "service_tracking": service_tracking,
                "project_id": project_id or False,
                "project_template_id": project_template_id or False,
                "taxes_id": [Command.set(self._demo_get_default_sale_tax(company).ids)],
            }
        )

    def _demo_build_quotation_lines(self, service_products):
        """2 sections x (>=2) subsections, one service product line each."""
        lines = []
        sequence = 10
        for section_index in range(2):
            lines.append(
                Command.create(
                    {
                        "display_type": "line_section",
                        "name": _("Secção %s") % (section_index + 1),
                        "sequence": sequence,
                    }
                )
            )
            sequence += 10
            for subsection_index in range(2):
                lines.append(
                    Command.create(
                        {
                            "display_type": "line_subsection",
                            "name": _("Subsecção %s.%s")
                            % (section_index + 1, subsection_index + 1),
                            "sequence": sequence,
                        }
                    )
                )
                sequence += 10
                product = service_products[
                    (section_index * 2 + subsection_index) % len(service_products)
                ]
                lines.append(
                    Command.create(
                        {
                            "product_id": product.product_variant_id.id,
                            "product_uom_qty": 1,
                            "sequence": sequence,
                        }
                    )
                )
                sequence += 10
        return lines

    def _demo_generate_sales(self, company, partner):
        """Quotation template with lines, applied to a new quotation."""
        log = []
        service = self._demo_get_or_create_product(
            company, _("Serviços de Consultoria"), 850.0, False
        )
        material = self._demo_get_or_create_product(
            company,
            self._demo_sector_name(_("Bens Diversos"), _("Materiais de Construção")),
            120.0,
            True,
        )
        template = self.env["sale.order.template"].create(
            {
                "name": _("Proposta Padrão"),
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

        # 3 project templates + 6 service products (3 create a task in the
        # existing project, 3 create a new project - copied from one of the
        # templates - per sale).
        templates = self._demo_get_or_create_project_templates(company)
        existing_project = self._demo_get_or_create_project(company)
        task_products = self.env["product.template"]
        for prod_name in [
            _("Consultoria Técnica (Horas)"),
            _("Suporte Pós-Venda"),
            _("Formação de Utilizadores"),
        ]:
            task_products |= self._demo_get_or_create_service_product(
                company,
                prod_name,
                95.0,
                "task_global_project",
                project_id=existing_project.id,
            )
        project_products = self.env["product.template"]
        for prod_name, tmpl in zip(
            [
                _("Implementação - Pacote Base"),
                _("Implementação - Pacote Standard"),
                _("Implementação - Pacote Premium"),
            ],
            templates,
        ):
            project_products |= self._demo_get_or_create_service_product(
                company,
                prod_name,
                2500.0,
                "task_in_project",
                project_template_id=tmpl.id,
            )
        log.append(
            _(
                "6 artigos de serviço criados (3 tarefa em projeto existente, "
                "3 novo projeto) e 3 modelos de projeto"
            )
        )

        # 2 quotations, each with 2 sections x 2 subsections, linked to a
        # distinct CRM opportunity.
        team = self.env.ref(
            "sales_team.team_sales_department", raise_if_not_found=False
        )
        all_service_products = list(task_products) + list(project_products)
        quotation_groups = [
            (
                _("Oportunidade - Proposta Detalhada A"),
                all_service_products[:3],
            ),
            (
                _("Oportunidade - Proposta Detalhada B"),
                all_service_products[3:],
            ),
        ]
        for opportunity_name, products_for_quotation in quotation_groups:
            opportunity = self.env["crm.lead"].create(
                {
                    "name": opportunity_name,
                    "type": "opportunity",
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "expected_revenue": 20000.0,
                    "team_id": team.id if team else False,
                    "user_id": self.env.uid,
                }
            )
            detailed_quotation = self.env["sale.order"].create(
                {
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "opportunity_id": opportunity.id,
                    "order_line": self._demo_build_quotation_lines(
                        products_for_quotation
                    ),
                }
            )
            detailed_quotation.pt_issue()
            log.append(
                _("Orçamento com secções criado: %s (oportunidade '%s')")
                % (detailed_quotation.name, opportunity.name)
            )

        # Confirm two more orders (one per product group) so the
        # service_tracking behaviour actually fires: this is what creates
        # the tasks/projects that Timesheets later logs hours against.
        confirmed_task_order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                # Belt-and-suspenders: _timesheet_service_generation()'s
                # task_global_project handling falls back to the order's own
                # project_id (sale_project/models/sale_order_line.py) if a
                # line's product-level project_id doesn't resolve for
                # whatever reason -- setting it here guarantees a valid
                # fallback instead of the "product needs a project" error.
                "project_id": existing_project.id,
                "order_line": [
                    Command.create(
                        {"product_id": p.product_variant_id.id, "product_uom_qty": 1}
                    )
                    for p in task_products
                ],
            }
        )
        confirmed_task_order.action_confirm()
        confirmed_project_order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                "order_line": [
                    Command.create(
                        {"product_id": p.product_variant_id.id, "product_uom_qty": 1}
                    )
                    for p in project_products
                ],
            }
        )
        confirmed_project_order.action_confirm()
        log.append(
            _(
                "2 encomendas confirmadas (%s, %s) para gerar as tarefas/"
                "projetos automaticamente"
            )
            % (confirmed_task_order.name, confirmed_project_order.name)
        )
        return log
