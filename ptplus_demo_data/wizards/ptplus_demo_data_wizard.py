##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Sector selection codes -- referenced from the other wizard files (via
# `self.sector == SECTOR_ENGENHARIA_CIVIL`) to gate sector-specific extras.
SECTOR_ENGENHARIA_CIVIL = "engenharia_civil"

SECTORS = [
    (SECTOR_ENGENHARIA_CIVIL, "Engenharia Civil"),
]


class PtplusDemoDataWizard(models.TransientModel):
    _name = "ptplus.demo.data.wizard"
    _description = "PT+ Demo Data Generator"

    company_name = fields.Char(required=True)
    vat = fields.Char(string="NIF")
    sector = fields.Selection(SECTORS, string="Sector de Atividade", required=True)
    street = fields.Char()
    city = fields.Char()
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one(
        "res.country", required=True, default=lambda self: self.env.ref("base.pt")
    )
    currency_id = fields.Many2one(
        "res.currency", required=True, default=lambda self: self.env.ref("base.EUR")
    )
    employee_count = fields.Integer(string="Nº de Colaboradores", default=15)
    phone = fields.Char()
    email = fields.Char()
    website = fields.Char()

    generate_fiscal_documents = fields.Boolean(
        string="Documentos Fiscais PT", default=True
    )
    generate_crm = fields.Boolean(string="CRM", default=True)
    generate_voip = fields.Boolean(string="VoIP", default=True)
    generate_sales = fields.Boolean(
        string="Vendas (templates e worksheet)", default=True
    )
    generate_project = fields.Boolean(
        string="Projectos e Tarefas (Documents)", default=True
    )
    generate_timesheets = fields.Boolean(string="Registo de Horas", default=True)
    generate_planning = fields.Boolean(string="Planeamento", default=True)
    generate_milestone_invoicing = fields.Boolean(
        string="Faturação por Milestones", default=True
    )
    generate_payroll = fields.Boolean(string="Salários", default=True)
    generate_email_marketing = fields.Boolean(string="Email Marketing", default=True)
    generate_sms = fields.Boolean(string="SMS", default=True)
    generate_whatsapp = fields.Boolean(string="WhatsApp", default=True)
    generate_marketing_automation = fields.Boolean(
        string="Marketing Automation", default=True
    )
    generate_helpdesk = fields.Boolean(string="Apoio ao Cliente", default=True)

    result_log = fields.Text(readonly=True)

    def _demo_company_vals(self):
        self.ensure_one()
        return {
            "name": self.company_name,
            "country_id": self.country_id.id,
            "currency_id": self.currency_id.id,
            "vat": self.vat or False,
            "street": self.street or False,
            "city": self.city or False,
            "zip": self.zip or False,
            "phone": self.phone or False,
            "email": self.email or False,
            "website": self.website or False,
        }

    def _demo_create_company(self):
        """Create the demo company and make it usable by the current user.

        ``res.company.create()`` already adds the new company to the current
        user's ``company_ids`` and (since ``country_id`` is set) schedules a
        precommit callback that loads the matching chart of accounts template
        -- see ``_demo_activate_pt_localization``.
        """
        self.ensure_one()
        # ``chart_template_load=True`` stops res.company.create() (base module)
        # from scheduling its own automatic chart-of-accounts loading: it would
        # otherwise auto-guess the generic core ``pt`` template instead of PT+'s
        # ``pt_base`` (which is what actually creates fiscal.document.type
        # records, see _demo_activate_pt_localization), and doing both would
        # load the chart twice.
        company = (
            self.env["res.company"]
            .sudo()
            .with_context(chart_template_load=True)
            .create(self._demo_company_vals())
        )
        sector_label = dict(self._fields["sector"].selection).get(self.sector)
        industry = self.env["res.partner.industry"].search(
            [("name", "=", sector_label)], limit=1
        )
        if not industry:
            industry = self.env["res.partner.industry"].create({"name": sector_label})
        company.partner_id.industry_id = industry
        return company

    def _demo_create_warehouse(self, company):
        """Create the company's default warehouse.

        Odoo only auto-creates one per company inside its test framework
        (``stock/models/res_company.py``, gated on ``current_test``) --
        outside of tests it must be created explicitly. This must happen
        *before* ``_demo_activate_pt_localization``: loading the chart
        template is what links the Delivery/Internal picking types to the
        GR/GA fiscal document types (see ``ptplus_stock/models/res_company.py``
        ``l10n_pt_create_default_fiscal_doc_types``), so if no warehouse
        exists yet at that point those documents never get linked.
        """
        self.ensure_one()
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1
        )
        if not warehouse:
            warehouse = self.env["stock.warehouse"].create(
                {
                    "name": _("Armazém Principal"),
                    "code": ("WH%s" % company.id)[:5],
                    "company_id": company.id,
                }
            )
        # A one-step warehouse's "Internal Transfers" picking type is
        # created inactive; the GA (Asset Transport Note) fiscal document
        # type only gets linked to it (in l10n_pt_create_default_fiscal_doc_types)
        # if an active internal picking type is found for the company.
        if not warehouse.int_type_id.active:
            warehouse.int_type_id.active = True
        return warehouse

    def _demo_activate_pt_localization(self, company):
        """Load the Portuguese chart of accounts and enable PT+ invoicing.

        ``pt_base`` (not the generic core ``pt`` template) is PT+'s own SNC
        chart -- loading it is what creates the company's default fiscal
        document types (invoice/stock/work/pay sections), see
        ``ptplus/models/account_chart_template.py``. ``ptplus``'s own test
        base (``ptplus/tests/common.py``) loads the same template.
        """
        self.ensure_one()
        self.env["account.chart.template"].try_loading(
            template_code="pt_base", company=company
        )
        company.pt_invoicing = True
        # "real-time" (the default) makes ptplus_saft compute SAF-T elements
        # synchronously inside pt_issue(), which for this company reaches
        # out to the AT webservice -- and a demo company has no real AT
        # credentials configured ("Webservice security error: empty
        # username or password."). "delayed" just flags elements as
        # "needed" for a cron to pick up later, with no live call.
        company.l10n_pt_saft_computing_method = "delayed"

    def _demo_is_civil_engineering(self):
        return self.sector == SECTOR_ENGENHARIA_CIVIL

    def _demo_sector_name(self, generic, civil_engineering):
        """Pick a label depending on the company's sector.

        Used for records that always get created (one is mandatory) but
        whose wording should only look sector-specific when it actually
        matches -- as opposed to additional records that only exist for a
        given sector at all (those are gated with _demo_is_civil_engineering
        directly in each generator method).
        """
        return civil_engineering if self._demo_is_civil_engineering() else generic

    def _demo_create_partner(self, company):
        """A single customer partner used across the generated documents."""
        self.ensure_one()
        return (
            self.env["res.partner"]
            .with_company(company)
            .create(
                {
                    "name": _("%s - Cliente Demo") % self.company_name,
                    "company_id": company.id,
                    "country_id": self.country_id.id,
                    "city": self.city or False,
                    "customer_rank": 1,
                }
            )
        )

    def action_generate_demo_data(self):
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("Only administrators can generate demo data."))

        company = self._demo_create_company()
        # Build the company-scoped recordset BEFORE creating anything else:
        # multi-company record rules (e.g. stock.location's "Location
        # multi-company") check against env.companies / allowed_company_ids,
        # which only reflects the new company once it's in this context --
        # res.users.company_ids being updated is not enough on its own for a
        # non-superuser admin. sudo() on top removes any remaining
        # per-model multi-company rule friction for this admin-only wizard.
        demo = (
            self.sudo()
            .with_company(company)
            .with_context(allowed_company_ids=(self.env.user.company_ids | company).ids)
        )
        demo._demo_create_warehouse(company)
        demo._demo_activate_pt_localization(company)
        partner = demo._demo_create_partner(company)

        log = [_("Company '%s' created and PT+ invoicing activated.") % company.name]

        steps = [
            (self.generate_fiscal_documents, demo._demo_generate_fiscal_documents),
            (self.generate_crm, demo._demo_generate_crm),
            (self.generate_voip, demo._demo_generate_voip),
            (self.generate_sales, demo._demo_generate_sales),
            (self.generate_project, demo._demo_generate_project),
            (self.generate_timesheets, demo._demo_generate_timesheets),
            (self.generate_planning, demo._demo_generate_planning),
            (
                self.generate_milestone_invoicing,
                demo._demo_generate_milestone_invoicing,
            ),
            (self.generate_payroll, demo._demo_generate_payroll),
            (self.generate_email_marketing, demo._demo_generate_email_marketing),
            (self.generate_sms, demo._demo_generate_sms),
            (self.generate_whatsapp, demo._demo_generate_whatsapp),
            (
                self.generate_marketing_automation,
                demo._demo_generate_marketing_automation,
            ),
            (self.generate_helpdesk, demo._demo_generate_helpdesk),
        ]
        # All-or-nothing: any step failing must abort the whole thing (no
        # company, no partial data) and surface a clear error, rather than
        # silently skipping that step and leaving an inconsistent demo
        # company behind.
        for enabled, step in steps:
            if not enabled:
                continue
            try:
                log.extend(step(company, partner) or [])
            except UserError:
                raise
            except Exception as exc:  # noqa: BLE001
                _logger.exception("PT+ demo data step %s failed", step.__name__)
                raise UserError(
                    _(
                        "Demo data generation failed at step '%(step)s': "
                        "%(error)s\n\nNothing was created."
                    )
                    % {"step": step.__name__, "error": exc}
                ) from exc

        self.result_log = "\n".join(log)
        return {
            "type": "ir.actions.act_window",
            "res_model": "ptplus.demo.data.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
