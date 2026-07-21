##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
import base64

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
        won_opportunity = False
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
            if stage == stages["won"] and not won_opportunity:
                won_opportunity = lead
        if won_opportunity:
            log += self._demo_generate_won_opportunity_order(
                company, partner, won_opportunity
            )
        return log

    def _demo_generate_won_opportunity_order(self, company, partner, opportunity):
        """A won opportunity needs an OR (quotation) that actually shows up
        on its "Quotations" smart button, plus a confirmed order whose
        auto-created project has documents in it.

        Both can't be the same sale.order: crm.lead.quotation_count only
        counts orders still in draft/sent state (sale_crm/models/
        crm_lead.py _get_lead_quotation_domain) -- once one is confirmed it
        moves to the separate "Orders" smart button instead. So this creates
        two distinct orders against the same opportunity: one left as a
        draft OR, one confirmed into the project-creating order.
        """
        log = []
        # Same 2 sections x 2 subsections shape as the other sectioned
        # quotations in _demo_generate_sales, and its lines must be service
        # articles configured to generate tasks/projects (task_global_project
        # / task_in_project) rather than a plain consulting line.
        existing_project = self._demo_get_or_create_project(company)
        quotation_products = self.env["product.template"]
        for prod_name in [
            _("Consultoria Especializada (Horas)"),
            _("Acompanhamento Técnico"),
        ]:
            quotation_products |= self._demo_get_or_create_service_product(
                company,
                prod_name,
                95.0,
                "task_global_project",
                project_id=existing_project.id,
            )
        for prod_name in [
            _("Implementação - Fase Inicial"),
            _("Implementação - Fase Final"),
        ]:
            quotation_products |= self._demo_get_or_create_service_product(
                company, prod_name, 2500.0, "task_in_project"
            )

        # The first product of the first section (Secção 1 / Subsecção 1.1,
        # per _demo_build_quotation_lines's ordering) gets a document
        # attached to it directly. product.template's "Documents" smart
        # button counts product.document (product/models/product_template.py
        # _get_product_document_domain), not documents.document -- that's
        # the Documents *app*'s own separate model, and unrelated here.
        first_product = list(quotation_products)[0]
        self.env["product.document"].create(
            {
                "name": "Ficha_Tecnica_%s.txt" % first_product.id,
                "res_model": "product.template",
                "res_id": first_product.id,
                "datas": base64.b64encode(
                    (_("Ficha técnica do artigo %s.") % first_product.name).encode()
                ),
                "company_id": company.id,
            }
        )
        log.append(
            _("Documento associado ao artigo '%s' (1ª linha da 1ª secção)")
            % first_product.name
        )

        quotation = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                "opportunity_id": opportunity.id,
                "order_line": self._demo_build_quotation_lines(
                    list(quotation_products)
                ),
            }
        )
        quotation.pt_issue()
        log.append(
            _("Orçamento (OR) com secções criado para a oportunidade ganha " "'%s': %s")
            % (opportunity.name, quotation.name)
        )

        product = self._demo_get_or_create_service_product(
            company, _("Implementação - Projeto Fechado"), 18000.0, "task_in_project"
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                "opportunity_id": opportunity.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.product_variant_id.id,
                            "product_uom_qty": 1,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        log.append(
            _("Orçamento confirmado para a oportunidade ganha '%s': %s")
            % (opportunity.name, order.name)
        )

        project = order.order_line.project_id
        if project:
            # sale_project names it after the order/product by default (e.g.
            # "NE A/00002 - Implementação - Projeto Fechado") -- same reason
            # as the other auto-created projects in _demo_generate_sales:
            # read like a real project instead of a document reference.
            project.name = (
                self._demo_sector_name(_("Projeto"), _("Obra"))
                + " - "
                + opportunity.name
            )
            root_folder = company.documents_project_folder_id
            project_folder = self.env["documents.document"].create(
                {
                    "name": project.name,
                    "type": "folder",
                    "folder_id": root_folder.id,
                    "company_id": company.id,
                }
            )
            project.documents_folder_id = project_folder.id
            documents_data = [
                ("Contrato_Assinado.txt", "Contrato assinado com o cliente."),
                ("Plano_de_Projeto.txt", "Plano de execução do projeto."),
            ]
            for filename, content in documents_data:
                self.env["documents.document"].create(
                    {
                        "name": filename,
                        "folder_id": project_folder.id,
                        "datas": base64.b64encode(content.encode()),
                        "res_model": "project.project",
                        "res_id": project.id,
                        "owner_id": self.env.uid,
                        "company_id": company.id,
                    }
                )
            log.append(
                _("Pasta de documentos criada para o projeto '%s' com %s documentos")
                % (project.name, len(documents_data))
            )
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
                # `summary` is added to voip.call by voip_ai (auto-installed
                # alongside voip+ai, both already demo_data dependencies).
                call.summary = next(transcripts)
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
                # Explicit, distinct sequence per line: sale_project processes
                # so_line_new_project sorted by (sequence, id) when deciding
                # whether to create a new project per line -- each of these 3
                # lines has its own product_template_id already, but giving
                # them an unambiguous processing order removes any residual
                # risk of that sort behaving unexpectedly.
                "order_line": [
                    Command.create(
                        {
                            "product_id": p.product_variant_id.id,
                            "product_uom_qty": 1,
                            "sequence": (index + 1) * 10,
                        }
                    )
                    for index, p in enumerate(project_products)
                ],
            }
        )
        confirmed_project_order.action_confirm()
        # sale_project names the auto-generated project after the order
        # (e.g. "NE A/00003") -- rename to something that reads like a real
        # project rather than a document reference.
        new_project_names = self._demo_sector_name(
            [_("Projeto Alfa"), _("Projeto Beta"), _("Projeto Gama")],
            [
                _("Obra - Condomínio no Porto"),
                _("Construção - Parque da Cidade"),
                _("Reabilitação - Edifício Histórico"),
            ],
        )
        for line, name in zip(confirmed_project_order.order_line, new_project_names):
            if line.project_id:
                line.project_id.name = name
        # Each new project only has the single auto-generated task -- add a
        # few more per project so Timesheets has more than one task to
        # distribute hours across per project.
        extra_task_names = self._demo_sector_name(
            [
                [_("Planeamento"), _("Execução"), _("Entrega")],
                [_("Planeamento"), _("Execução"), _("Entrega")],
                [_("Planeamento"), _("Execução"), _("Entrega")],
            ],
            [
                [
                    _("Escavação e Fundações"),
                    _("Estrutura e Alvenaria"),
                    _("Acabamentos e Entrega"),
                ],
                [
                    _("Terraplanagem"),
                    _("Instalação de Equipamentos"),
                    _("Paisagismo"),
                ],
                [
                    _("Levantamento e Diagnóstico"),
                    _("Recuperação de Fachada"),
                    _("Requalificação Interior"),
                ],
            ],
        )
        extra_task_states = ["01_in_progress", "04_waiting_normal", "1_done"]
        for line, names in zip(confirmed_project_order.order_line, extra_task_names):
            if not line.project_id:
                continue
            stage_by_state = self._demo_get_or_create_task_stages(line.project_id)
            for name, state in zip(names, extra_task_states):
                self.env["project.task"].create(
                    {
                        "name": name,
                        "project_id": line.project_id.id,
                        "company_id": company.id,
                        "user_ids": [Command.set([self.env.uid])],
                        "state": state,
                        "stage_id": stage_by_state[state].id,
                    }
                )
        # Tasks that sale_project auto-creates on confirmation don't always
        # get a default kanban stage -- backfill any left without one.
        self._demo_ensure_task_stages(company)
        log.append(
            _(
                "2 encomendas confirmadas (%s, %s) para gerar as tarefas/"
                "projetos automaticamente, com 3 tarefas extra por projeto novo"
            )
            % (confirmed_task_order.name, confirmed_project_order.name)
        )
        return log
