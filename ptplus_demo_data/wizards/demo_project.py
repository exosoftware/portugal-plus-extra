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
        stage_by_state = self._demo_get_or_create_task_stages(project)
        for name, topic, state in tasks_data:
            self.env["project.task"].create(
                {
                    "name": name,
                    "project_id": project.id,
                    "company_id": company.id,
                    "user_ids": [Command.set([self.env.uid])],
                    "tag_ids": [Command.set([topic_tags[topic].id])],
                    "state": state,
                    "stage_id": stage_by_state[state].id,
                }
            )
        log.append(_("%s tarefas criadas, uma por tópico") % len(tasks_data))
        return log

    def _demo_get_or_create_task_stages(self, project):
        """Kanban stages for a project, one per task state used above.

        project.task.stage_id is a compute(store=True, readonly=False)
        field, but it doesn't reliably default to something via plain
        ORM create() (nor for tasks sale_project auto-creates on order
        confirmation) -- setting it explicitly avoids tasks with no stage.
        """
        stage_names = {
            "01_in_progress": (_("Em Curso"), 1, False),
            "02_changes_requested": (_("Alterações Pedidas"), 2, False),
            "04_waiting_normal": (_("Em Espera"), 3, False),
            "1_done": (_("Concluído"), 4, True),
        }
        stages = {}
        for state, (name, sequence, fold) in stage_names.items():
            stage = self.env["project.task.type"].search(
                [("name", "=", name), ("project_ids", "in", project.id)], limit=1
            )
            if not stage:
                stage = self.env["project.task.type"].create(
                    {
                        "name": name,
                        "sequence": sequence,
                        "fold": fold,
                        "project_ids": [Command.link(project.id)],
                    }
                )
            stages[state] = stage
        return stages

    def _demo_ensure_task_stages(self, company):
        """Backfill stage_id for any task left without one.

        Tasks that sale_project auto-creates on order confirmation
        (service_tracking) don't always get a default kanban stage.
        """
        tasks_without_stage = self.env["project.task"].search(
            [("company_id", "=", company.id), ("stage_id", "=", False)]
        )
        for task in tasks_without_stage:
            stage = self.env["project.task.type"].search(
                [("project_ids", "in", task.project_id.id)], order="sequence", limit=1
            )
            if not stage:
                stage = self.env["project.task.type"].create(
                    {
                        "name": _("A Fazer"),
                        "sequence": 1,
                        "project_ids": [Command.link(task.project_id.id)],
                    }
                )
            task.stage_id = stage.id

    def _demo_split_daily_hours(self, daily_total, num_tasks):
        """Split a day's total hours across num_tasks lines, each a multiple
        of 0.5, summing exactly to daily_total (so no line -- and therefore
        no task -- can ever exceed the day's own total)."""
        if num_tasks <= 1:
            return [daily_total]
        portions = []
        remaining = daily_total
        for tasks_left in range(num_tasks, 1, -1):
            # Leave at least 0.5h for each remaining task after this one.
            max_portion = remaining - 0.5 * (tasks_left - 1)
            portion = round(random.uniform(0.5, max(0.5, max_portion)) * 2) / 2
            portion = min(portion, remaining - 0.5 * (tasks_left - 1))
            portions.append(portion)
            remaining -= portion
        portions.append(remaining)
        return portions

    def _demo_generate_timesheets(self, company, partner):
        log = []
        roster = list(self._demo_get_or_create_employee_roster(company))
        tasks = list(self.env["project.task"].search([("company_id", "=", company.id)]))
        if not tasks:
            return log
        hour_uom = self.env.ref("uom.product_uom_hour")
        today = fields.Date.context_today(self)
        # Last 30 days, weekdays only -- nobody logs time on Sat/Sun.
        MAX_DAILY_HOURS = 8.0
        weekdays = [
            today - timedelta(days=offset)
            for offset in range(30)
            if (today - timedelta(days=offset)).weekday() < 5
        ]
        count = 0
        for employee in roster:
            # "Almost every day", not literally every day -- randomly skip
            # ~15% of weekdays (day off, sick, etc.) for realism.
            worked_days = [d for d in weekdays if random.random() > 0.15]
            for date in worked_days:
                daily_total = round(random.uniform(3.0, MAX_DAILY_HOURS) * 2) / 2
                num_tasks_today = min(random.choice([1, 1, 2, 2, 3]), len(tasks))
                day_tasks = random.sample(tasks, num_tasks_today)
                for task, hours in zip(
                    day_tasks,
                    self._demo_split_daily_hours(daily_total, num_tasks_today),
                ):
                    if hours <= 0:
                        continue
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
            _(
                "Registo de horas criado: %s lançamentos para %s colaboradores "
                "nos últimos 30 dias (máx. %s horas/dia, sem fins de semana)"
            )
            % (count, len(roster), int(MAX_DAILY_HOURS))
        )
        return log

    def _demo_generate_planning(self, company, partner):
        log = []
        # By this point (planning runs after project/sales), the company
        # already has several distinct projects: the main one plus whatever
        # sale_project auto-created from the won opportunity and confirmed
        # orders in _demo_generate_sales -- spread slots across all of them
        # instead of just the main project, so Planning doesn't show one
        # identical block for every employee.
        # Exclude project templates (is_template=True, never meant to hold
        # real work) and the auto-created internal project -- only real
        # client-facing projects should get planning slots.
        projects = list(
            self.env["project.project"].search(
                [
                    ("company_id", "=", company.id),
                    ("is_template", "=", False),
                    ("is_internal_project", "=", False),
                ]
            )
        )
        if not projects:
            projects = [self._demo_get_or_create_project(company)]
        random.shuffle(projects)
        roster = list(self._demo_get_or_create_employee_roster(company))
        role = self._demo_get_or_create_tag(
            "planning.role",
            self._demo_sector_name(_("Consultor"), _("Engenheiro Civil")),
        )
        today = fields.Datetime.now()
        for index, employee in enumerate(roster):
            project = projects[index % len(projects)]
            # Stagger start dates over the next 3 weeks and vary each slot's
            # length (1-5 weeks) so dates don't all line up either.
            start = today + timedelta(days=random.randint(-5, 15))
            end = start + timedelta(weeks=random.randint(1, 5))
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
            _("%s turnos de planeamento criados em %s projetos, com datas variadas")
            % (len(roster), len(projects))
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

        # Every employee gets several leave requests totalling 17-22 days
        # (close to their full 22-day allocation, like real vacation
        # planning). Each request is Monday-anchored and spans at most 5
        # working days, so its actual day count is predictable up front
        # without depending on the employee's resource calendar. The last
        # request per employee is left pending; earlier ones are approved,
        # giving every employee a mix of both.
        total_pending = 0
        total_approved = 0
        for emp_index, employee in enumerate(roster):
            target_days = 17 + (emp_index % 6)
            cursor = today + timedelta(days=10 + emp_index * 12)
            periods = []
            remaining = target_days
            while remaining > 0:
                days = min(5, remaining)
                start = cursor + timedelta(days=(7 - cursor.weekday()) % 7)
                periods.append((start, days))
                remaining -= days
                cursor = start + timedelta(days=days + 7)
            for period_index, (start, days) in enumerate(periods):
                leave = self.env["hr.leave"].create(
                    {
                        "employee_id": employee.id,
                        "holiday_status_id": leave_type.id,
                        "request_date_from": start,
                        "request_date_to": start + timedelta(days=days - 1),
                    }
                )
                if period_index < len(periods) - 1:
                    leave.action_approve()
                    total_approved += 1
                else:
                    total_pending += 1
        log.append(
            _(
                "Pedidos de férias criados para %(count)s colaboradores "
                "(17 a 22 dias cada; %(approved)s pedidos aprovados, "
                "%(pending)s pendentes)"
            )
            % {
                "count": len(roster),
                "approved": total_approved,
                "pending": total_pending,
            }
        )
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
