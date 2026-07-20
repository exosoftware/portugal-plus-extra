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

    def _demo_get_or_create_employee_roster(self, company):
        """10 employees across 3 departments, 2 hierarchy levels.

        1 top-level manager + 1 department manager per department (reporting
        to the top manager) + 2 regular employees per department (reporting
        to their department manager) = 1 + 3 + 6 = 10, so the org chart shows
        both levels.
        """
        existing = self.env["hr.employee"].search([("company_id", "=", company.id)])
        if len(existing) >= 10:
            return existing

        top_manager = self.env["hr.employee"].search(
            [("name", "=", _("Diretor Geral")), ("company_id", "=", company.id)],
            limit=1,
        )
        if not top_manager:
            top_manager = self.env["hr.employee"].create(
                {
                    "name": _("Diretor Geral"),
                    "company_id": company.id,
                    "job_title": _("Diretor Geral"),
                }
            )
        # Linking to the acting user means the timesheets/tasks/planning
        # generated for this roster show up under "My Timesheets"/"My
        # Tasks" without having to clear the default filter.
        if not top_manager.user_id:
            top_manager.user_id = self.env.uid

        roster = top_manager
        for dept_name in [_("Técnico"), _("Financeiro"), _("Comercial")]:
            department = self.env["hr.department"].search(
                [("name", "=", dept_name), ("company_id", "=", company.id)], limit=1
            )
            if not department:
                manager = self.env["hr.employee"].create(
                    {
                        "name": _("Responsável de %s") % dept_name,
                        "company_id": company.id,
                        "job_title": _("Responsável de Departamento"),
                        "parent_id": top_manager.id,
                    }
                )
                department = self.env["hr.department"].create(
                    {
                        "name": dept_name,
                        "company_id": company.id,
                        "manager_id": manager.id,
                    }
                )
                manager.department_id = department.id
            roster |= department.manager_id
            for i in range(1, 3):
                emp_name = _("%s - Colaborador %s") % (dept_name, i)
                employee = self.env["hr.employee"].search(
                    [("name", "=", emp_name), ("company_id", "=", company.id)], limit=1
                )
                if not employee:
                    employee = self.env["hr.employee"].create(
                        {
                            "name": emp_name,
                            "company_id": company.id,
                            "department_id": department.id,
                            "parent_id": department.manager_id.id,
                            "job_title": self._demo_sector_name(
                                _("Consultor"), _("Engenheiro Civil")
                            ),
                        }
                    )
                roster |= employee
        return roster

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
        roster = list(self._demo_get_or_create_employee_roster(company))
        tasks = self.env["project.task"].search([("company_id", "=", company.id)])
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
        weekdays = [
            previous_monday + timedelta(days=i)
            for i in range((today - previous_monday).days + 1)
            if (previous_monday + timedelta(days=i)).weekday() < 5
        ]
        count = 0
        for task in tasks:
            entry_count = random.randint(3, 5)
            task_employees = random.sample(roster, min(len(roster), entry_count))
            while len(task_employees) < entry_count:
                task_employees.append(random.choice(roster))
            task_dates = random.sample(weekdays, min(len(weekdays), entry_count))
            while len(task_dates) < entry_count:
                task_dates.append(random.choice(weekdays))
            for employee, date in zip(task_employees, task_dates):
                hours = round(random.uniform(1.0, 6.0) * 2) / 2
                self.env["account.analytic.line"].create(
                    {
                        "name": _("Trabalho realizado"),
                        "employee_id": employee.id,
                        "project_id": task.project_id.id,
                        "task_id": task.id,
                        "product_uom_id": hour_uom.id,
                        "unit_amount": hours,
                        "date": date,
                    }
                )
                count += 1
        log.append(
            _("Registo de horas criado: %s lançamentos em %s tarefas")
            % (count, len(tasks))
        )
        return log

    def _demo_generate_planning(self, company, partner):
        log = []
        project = self._demo_get_or_create_project(company)
        roster = self._demo_get_or_create_employee_roster(company)
        role = self._demo_get_or_create_tag(
            "planning.role",
            self._demo_sector_name(_("Consultor"), _("Engenheiro Civil")),
        )
        start = fields.Datetime.now()
        end = start + timedelta(days=31)
        for employee in roster:
            self.env["planning.slot"].create(
                {
                    "resource_id": employee.resource_id.id,
                    "role_id": role.id,
                    "project_id": project.id,
                    "start_datetime": start,
                    "end_datetime": end,
                    "company_id": company.id,
                }
            )
        log.append(
            _("%s turnos de planeamento criados (1 mês cada, um por colaborador)")
            % len(roster)
        )
        log += self._demo_generate_time_off(company, roster)
        return log

    def _demo_generate_time_off(self, company, roster):
        log = []
        leave_type = self.env["hr.leave.type"].search(
            [("name", "=", _("Férias")), ("company_id", "in", [company.id, False])],
            limit=1,
        )
        if not leave_type:
            leave_type = self.env["hr.leave.type"].create(
                {
                    "name": _("Férias"),
                    "company_id": company.id,
                    "time_type": "leave",
                    "requires_allocation": True,
                    "request_unit": "day",
                    "allocation_validation_type": "hr",
                    "leave_validation_type": "hr",
                }
            )
        today = fields.Date.context_today(self)
        year_start = today.replace(month=1, day=1)
        for employee in roster:
            allocation = self.env["hr.leave.allocation"].create(
                {
                    "employee_id": employee.id,
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 22,
                    "date_from": year_start,
                }
            )
            allocation.action_approve()
        log.append(
            _("Alocação de 22 dias de férias criada para %s colaboradores")
            % len(roster)
        )

        # 4 absences: 2 left pending approval, 2 already approved.
        leave_employees = list(roster)[:4]
        for index, employee in enumerate(leave_employees):
            leave_start = today + timedelta(days=10 + index * 7)
            leave = self.env["hr.leave"].create(
                {
                    "employee_id": employee.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": leave_start,
                    "request_date_to": leave_start + timedelta(days=4),
                }
            )
            if index >= 2:
                leave.action_approve()
        log.append(_("4 pedidos de ausência criados (2 pendentes, 2 aprovados)"))
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
