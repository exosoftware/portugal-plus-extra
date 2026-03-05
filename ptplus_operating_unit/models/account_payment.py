# Copyright 2019 Exo Software Lda.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.onchange("operating_unit_id")
    def _onchange_operating_unit(self):
        # super(AccountPayment, self)._onchange_operating_unit()
        if self.source_billing:
            domain = self._pt_get_fiscal_doc_domain(self.source_billing)
            fiscal_doc = self._pt_get_fiscal_doc_selection(domain, limit=1)
            if fiscal_doc:
                self.fiscal_document_type_id = fiscal_doc

    def _pt_get_fiscal_doc_domain(self, source_billing, vals=None):
        # Initialize on super
        domain = super()._pt_get_fiscal_doc_domain(source_billing, vals)

        # add operating unit filter to domain
        if "operating_unit_id" in self._fields:
            operating_unit_id = (
                vals
                and vals.get("operating_unit_id", False)
                or self.operating_unit_id.id
            )

            domain.extend(
                [
                    ("operating_unit_id", "in", (False, operating_unit_id)),
                ]
            )
        return domain
