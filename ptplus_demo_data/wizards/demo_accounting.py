##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
import random
from datetime import timedelta

from odoo import _, fields, models
from odoo.fields import Command


class PtplusDemoDataWizard(models.TransientModel):
    _inherit = "ptplus.demo.data.wizard"

    def _demo_get_expense_account(self, company):
        return self.env["account.account"].search(
            [("company_ids", "in", company.id), ("account_type", "=", "expense")],
            limit=1,
        )

    def _demo_get_default_purchase_tax(self, company):
        return self.env["account.tax"].search(
            [
                ("company_id", "=", company.id),
                ("type_tax_use", "=", "purchase"),
                ("l10n_pt_genre", "=", "IVA"),
                ("pt_vat_tax_type", "=", "NOR"),
                ("pt_vat_subject", "=", "ogs"),
            ],
            order="amount desc",
            limit=1,
        )

    def _demo_get_or_create_vendor(self, company):
        name = _("%s - Fornecedor Demo") % self.company_name
        vendor = self.env["res.partner"].search(
            [("name", "=", name), ("company_id", "=", company.id)], limit=1
        )
        if vendor:
            return vendor
        return (
            self.env["res.partner"]
            .with_company(company)
            .create(
                {
                    "name": name,
                    "company_id": company.id,
                    "country_id": self.country_id.id,
                    "supplier_rank": 1,
                }
            )
        )

    def _demo_generate_invoices(self, company, partner):
        log = []
        income_account = self._demo_get_income_account(company)
        expense_account = self._demo_get_expense_account(company)
        purchase_tax = self._demo_get_default_purchase_tax(company)
        service = self._demo_get_or_create_product(
            company, _("Serviços de Consultoria"), 850.0, False
        )
        vendor = self._demo_get_or_create_vendor(company)
        today = fields.Date.context_today(self)

        sale_states = ["draft", "draft", "posted", "posted", "posted"]
        for index, state in enumerate(sale_states):
            invoice = self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": partner.id,
                    "company_id": company.id,
                    # Never earlier than today, never mind past: PT+ requires
                    # each posted document of the same fiscal type (FT) to
                    # have a date that isn't before the previous one's
                    # (pt_check_doc_no in ptplus/models/fiscal_document.py).
                    # _demo_generate_fiscal_documents (an earlier step) already
                    # posts FT documents dated today, so anything backdated
                    # here would be "prior to the last of the same kind" --
                    # count forward from today instead.
                    "invoice_date": today + timedelta(days=index),
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": service.product_variant_id.id,
                                "quantity": 1,
                                "price_unit": 400.0 + index * 75,
                                "account_id": income_account.id,
                            }
                        )
                    ],
                }
            )
            if state == "posted":
                invoice.action_post()
        log.append(
            _("5 faturas de venda criadas (%s rascunho, %s validadas)")
            % (sale_states.count("draft"), sale_states.count("posted"))
        )

        purchase_states = ["draft", "draft", "posted", "posted", "posted"]
        for index, state in enumerate(purchase_states):
            bill = self.env["account.move"].create(
                {
                    "move_type": "in_invoice",
                    "partner_id": vendor.id,
                    "company_id": company.id,
                    # Same reasoning as the sale invoices above -- kept
                    # consistent even though vendor bills aren't PT+ fiscal
                    # documents themselves.
                    "invoice_date": today + timedelta(days=index),
                    "ref": _("Fatura Fornecedor %s") % (index + 1),
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": _("Serviços/Materiais adquiridos"),
                                "quantity": 1,
                                "price_unit": 250.0 + index * 60,
                                "account_id": expense_account.id,
                                "tax_ids": [Command.set(purchase_tax.ids)],
                            }
                        )
                    ],
                }
            )
            if state == "posted":
                bill.action_post()
        log.append(
            _("5 faturas de compra criadas (%s rascunho, %s validadas)")
            % (purchase_states.count("draft"), purchase_states.count("posted"))
        )
        return log

    def _demo_generate_bank_sync(self, company):
        log = []
        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", company.id)], limit=1
        )
        if not bank_journal:
            bank_journal = self.env["account.journal"].create(
                {
                    "name": _("Banco Demo"),
                    "code": "BNKD",
                    "type": "bank",
                    "company_id": company.id,
                }
            )
        # Any non-suspense account works as the "already matched" counterpart
        # -- see account.bank.statement.line.create()'s handling of the
        # counterpart_account_id key (account_bank_statement_line.py).
        other_account = self._demo_get_expense_account(company)
        today = fields.Date.context_today(self)

        lines = []
        for index in range(10):
            vals = {
                "journal_id": bank_journal.id,
                "date": today - timedelta(days=index),
                "payment_ref": _("Movimento Bancário %s") % (index + 1),
                "amount": round(
                    random.uniform(50.0, 800.0) * (1 if index % 2 == 0 else -1), 2
                ),
            }
            if index < 5:
                # Reconciled-looking: counterpart posted to a real account
                # instead of the journal's suspense account.
                vals["counterpart_account_id"] = other_account.id
            lines.append(Command.create(vals))

        statement = self.env["account.bank.statement"].create(
            {
                "name": _("Sincronização Bancária Demo"),
                "balance_start": 0.0,
                "line_ids": lines,
            }
        )
        reconciled = len(statement.line_ids.filtered("is_reconciled"))
        log.append(
            _(
                "Extrato bancário criado: %s movimentos (%s conciliados, %s por conciliar)"
            )
            % (
                len(statement.line_ids),
                reconciled,
                len(statement.line_ids) - reconciled,
            )
        )
        return log

    def _demo_generate_accounting(self, company, partner):
        log = self._demo_generate_invoices(company, partner)
        log += self._demo_generate_bank_sync(company)
        return log
