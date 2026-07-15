##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
import base64
from datetime import timedelta

from odoo import _, fields, models
from odoo.fields import Command


class PtplusDemoDataWizard(models.TransientModel):
    _inherit = "ptplus.demo.data.wizard"

    def _demo_get_or_create_project(self, company):
        name = _("Obra - %s") % company.name
        project = self.env["project.project"].search(
            [("name", "=", name), ("company_id", "=", company.id)], limit=1
        )
        if project:
            return project
        return self.env["project.project"].create(
            {
                "name": name,
                "company_id": company.id,
                "partner_id": False,
            }
        )

    def _demo_get_or_create_employee(self, company):
        name = _("Colaborador Demo")
        employee = self.env["hr.employee"].search(
            [("name", "=", name), ("company_id", "=", company.id)], limit=1
        )
        if not employee:
            employee = self.env["hr.employee"].create(
                {
                    "name": name,
                    "company_id": company.id,
                    "job_title": _("Engenheiro Civil"),
                }
            )
        # Linking the demo employee to the acting user means the timesheets/
        # tasks generated for it show up under "My Timesheets"/"My Tasks"
        # without the user having to clear the default filter.
        if not employee.user_id:
            employee.user_id = self.env.uid
        return employee

    def _demo_get_or_create_tag(self, model, name):
        tag = self.env[model].search([("name", "=", name)], limit=1)
        if tag:
            return tag
        return self.env[model].create({"name": name})

    def _demo_generate_project(self, company, partner):
        log = []
        project = self._demo_get_or_create_project(company)
        log.append(_("Projeto criado: %s") % project.name)

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

        departments = [_("Técnico"), _("Financeiro"), _("Comercial")]
        dept_folders = {}
        dept_tags = {}
        for dept in departments:
            dept_folders[dept] = self.env["documents.document"].create(
                {
                    "name": dept,
                    "type": "folder",
                    "folder_id": project_folder.id,
                    "company_id": company.id,
                }
            )
            dept_tags[dept] = self._demo_get_or_create_tag(
                "documents.tag", _("Departamento: %s") % dept
            )
        status_tags = {
            status: self._demo_get_or_create_tag(
                "documents.tag", _("Estado: %s") % status
            )
            for status in [_("A Enviar"), _("Enviado"), _("Aprovado")]
        }

        documents_data = [
            (
                _("Técnico"),
                "Memoria_Descritiva.txt",
                _("A Enviar"),
                "Memória descritiva do projeto.",
            ),
            (
                _("Técnico"),
                "Projeto_de_Execucao.txt",
                _("Enviado"),
                "Projeto de execução.",
            ),
            (
                _("Financeiro"),
                "Orcamento_Obra.txt",
                _("Aprovado"),
                "Orçamento detalhado da obra.",
            ),
            (
                _("Comercial"),
                "Proposta_Comercial.txt",
                _("Enviado"),
                "Proposta comercial enviada ao cliente.",
            ),
        ]
        for dept, filename, status, content in documents_data:
            self.env["documents.document"].create(
                {
                    "name": filename,
                    "folder_id": dept_folders[dept].id,
                    "datas": base64.b64encode(content.encode()),
                    "res_model": "project.project",
                    "res_id": project.id,
                    "owner_id": self.env.uid,
                    "tag_ids": [
                        Command.set([dept_tags[dept].id, status_tags[status].id])
                    ],
                    "company_id": company.id,
                }
            )
        log.append(
            _(
                "Pasta de documentos do projeto criada com 3 departamentos e 4 documentos"
            )
        )

        topics = [_("Estrutura"), _("Fundações"), _("Acabamentos"), _("Licenciamento")]
        topic_tags = {
            t: self._demo_get_or_create_tag("project.tags", t) for t in topics
        }
        tasks_data = [
            (_("Levantamento Topográfico"), topics[0], "1_done"),
            (_("Cálculo de Fundações"), topics[1], "01_in_progress"),
            (_("Acabamentos Interiores"), topics[2], "04_waiting_normal"),
            (_("Licenciamento Camarário"), topics[3], "02_changes_requested"),
        ]
        for name, topic, state in tasks_data:
            self.env["project.task"].create(
                {
                    "name": name,
                    "project_id": project.id,
                    "company_id": company.id,
                    "user_ids": [Command.set([self.env.uid])],
                    "tag_ids": [Command.set([topic_tags[topic].id])],
                    "state": state,
                }
            )
        log.append(_("4 tarefas criadas, uma por tópico da obra"))
        return log

    def _demo_generate_timesheets(self, company, partner):
        log = []
        project = self._demo_get_or_create_project(company)
        employee = self._demo_get_or_create_employee(company)
        tasks = self.env["project.task"].search([("project_id", "=", project.id)])
        hour_uom = self.env.ref("uom.product_uom_hour")
        today = fields.Date.context_today(self)
        hours_by_day = [8.0, 6.5, 4.0]
        count = 0
        for task in tasks:
            for day_offset, hours in enumerate(hours_by_day):
                self.env["account.analytic.line"].create(
                    {
                        "name": _("Trabalho realizado"),
                        "employee_id": employee.id,
                        "project_id": project.id,
                        "task_id": task.id,
                        "product_uom_id": hour_uom.id,
                        "unit_amount": hours,
                        "date": today - timedelta(days=day_offset),
                    }
                )
                count += 1
        log.append(
            _("Registo de horas criado: %s lançamentos em %s tarefa(s)")
            % (count, len(tasks))
        )
        return log

    def _demo_generate_planning(self, company, partner):
        log = []
        project = self._demo_get_or_create_project(company)
        employee = self._demo_get_or_create_employee(company)
        role = self._demo_get_or_create_tag("planning.role", _("Engenheiro Civil"))
        start = fields.Datetime.now()
        self.env["planning.slot"].create(
            {
                "resource_id": employee.resource_id.id,
                "role_id": role.id,
                "project_id": project.id,
                "start_datetime": start,
                "end_datetime": start + timedelta(hours=8),
                "company_id": company.id,
            }
        )
        log.append(_("Turno de planeamento criado para %s") % employee.name)
        return log

    def _demo_generate_milestone_invoicing(self, company, partner):
        log = []
        project = self._demo_get_or_create_project(company)
        milestone_product = self._demo_get_or_create_product(
            company, _("Fase de Projeto (Milestone)"), 5000.0, False
        )
        milestone_product.service_policy = "delivered_milestones"

        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": milestone_product.product_variant_id.id,
                            "product_uom_qty": 1,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        line = order.order_line[0]
        line.project_id = project.id

        milestone = self.env["project.milestone"].create(
            {
                "name": _("Entrega do Projeto de Execução"),
                "project_id": project.id,
                "sale_line_id": line.id,
                "deadline": fields.Date.add(fields.Date.context_today(self), days=30),
            }
        )
        milestone.is_reached = True
        log.append(
            _("Milestone de faturação criado: %s (Encomenda %s)")
            % (milestone.name, order.name)
        )
        return log
