##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
import base64
import random
from datetime import timedelta

from odoo import _, fields, models
from odoo.fields import Command


class PtplusDemoDataWizard(models.TransientModel):
    _inherit = "ptplus.demo.data.wizard"

    def _demo_get_or_create_project(self, company):
        name = self._demo_sector_name(_("Projeto"), _("Obra")) + " - " + company.name
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
                    "job_title": self._demo_sector_name(
                        _("Consultor"), _("Engenheiro Civil")
                    ),
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
                "Especificacao_Tecnica.txt",
                _("A Enviar"),
                "Especificação técnica do projeto.",
            ),
            (
                _("Financeiro"),
                "Orcamento_do_Projeto.txt",
                _("Aprovado"),
                "Orçamento detalhado do projeto.",
            ),
            (
                _("Comercial"),
                "Proposta_Comercial.txt",
                _("Enviado"),
                "Proposta comercial enviada ao cliente.",
            ),
        ]
        if self._demo_is_civil_engineering():
            documents_data += [
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
                "Pasta de documentos do projeto criada com 3 departamentos e %s documentos"
            )
            % len(documents_data)
        )

        tasks_data = [
            (_("Planeamento"), _("Planeamento"), "1_done"),
            (_("Execução"), _("Execução"), "01_in_progress"),
            (
                _("Controlo de Qualidade"),
                _("Controlo de Qualidade"),
                "04_waiting_normal",
            ),
            (_("Entrega Final"), _("Entrega"), "02_changes_requested"),
        ]
        if self._demo_is_civil_engineering():
            tasks_data += [
                (_("Levantamento Topográfico"), _("Estrutura"), "1_done"),
                (_("Cálculo de Fundações"), _("Fundações"), "01_in_progress"),
                (_("Acabamentos Interiores"), _("Acabamentos"), "04_waiting_normal"),
                (
                    _("Licenciamento Camarário"),
                    _("Licenciamento"),
                    "02_changes_requested",
                ),
            ]
        topic_tags = {
            topic: self._demo_get_or_create_tag("project.tags", topic)
            for _, topic, _ in tasks_data
        }
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
        log.append(_("%s tarefas criadas, uma por tópico") % len(tasks_data))
        return log

    def _demo_generate_timesheets(self, company, partner):
        log = []
        project = self._demo_get_or_create_project(company)
        employee = self._demo_get_or_create_employee(company)
        tasks = self.env["project.task"].search([("project_id", "=", project.id)])
        if not tasks:
            return log
        hour_uom = self.env.ref("uom.product_uom_hour")
        today = fields.Date.context_today(self)
        # Every weekday (Mon-Fri) of the previous ISO week, plus every
        # weekday of the current week up to today -- anchored on actual
        # week boundaries so the previous week is always fully covered,
        # regardless of which weekday "today" falls on.
        this_monday = today - timedelta(days=today.weekday())
        previous_monday = this_monday - timedelta(days=7)
        dates = [
            previous_monday + timedelta(days=i)
            for i in range((today - previous_monday).days + 1)
            if (previous_monday + timedelta(days=i)).weekday() < 5
        ]
        count = 0
        for idx, date in enumerate(dates):
            total_hours = round(random.uniform(3.0, 9.0) * 2) / 2
            if len(tasks) > 1 and random.random() < 0.4:
                task_a, task_b = random.sample(list(tasks), 2)
                hours_a = round(random.uniform(1.5, total_hours - 1.5) * 2) / 2
                day_entries = [(task_a, hours_a), (task_b, total_hours - hours_a)]
            else:
                day_entries = [(tasks[idx % len(tasks)], total_hours)]
            for task, hours in day_entries:
                self.env["account.analytic.line"].create(
                    {
                        "name": _("Trabalho realizado"),
                        "employee_id": employee.id,
                        "project_id": project.id,
                        "task_id": task.id,
                        "product_uom_id": hour_uom.id,
                        "unit_amount": hours,
                        "date": date,
                    }
                )
                count += 1
        log.append(
            _("Registo de horas criado: %s lançamentos em %s dias úteis")
            % (count, len(dates))
        )
        return log

    def _demo_generate_planning(self, company, partner):
        log = []
        project = self._demo_get_or_create_project(company)
        employee = self._demo_get_or_create_employee(company)
        role = self._demo_get_or_create_tag(
            "planning.role",
            self._demo_sector_name(_("Consultor"), _("Engenheiro Civil")),
        )
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
                "name": self._demo_sector_name(
                    _("Entrega Final do Projeto"), _("Entrega do Projeto de Execução")
                ),
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
