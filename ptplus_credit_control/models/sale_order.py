# Copyright 2026 Exo Software, Lda. (<https://exosoftware.pt>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        """Evaluate the financial risk *before* PT+ issues the fiscal document.

        ``ptplus_sale.action_confirm`` performs irreversible fiscal work in its
        own override body -- archival copy of the quotation, OR->NE document
        type change and ``pt_issue`` (serial numbering + signing) -- *before*
        delegating to ``super()``. The OCA ``sale_financial_risk`` gate sits
        further down the ``super()`` chain and, when the credit limit is
        exceeded, *returns* a wizard action instead of raising. So the base
        confirmation never runs (the order stays in ``sent``) yet the
        transaction commits, persisting PT+'s partial work: the order is left as
        a fully issued NE stuck in ``sent`` plus a spurious quotation copy, and
        any retry collides with the already consumed fiscal number
        (``sale_order_number_unique_index``). Clicking "Cancel" on the wizard
        cannot undo it because the transaction is already committed.

        This module depends on both ``ptplus_sale`` and ``sale_financial_risk``,
        so this override is the most derived one in the MRO and runs first.
        By replaying the exact OCA risk gate here -- ahead of ``super()`` and
        therefore ahead of every PT+ fiscal operation -- the credit check always
        precedes any document issuing: when the risk is exceeded we return the
        very same wizard without PT+ ever touching the document; otherwise
        ``super()`` proceeds normally (the OCA gate re-checks harmlessly).

        Kept in sync with ``sale_financial_risk/models/sale.py::action_confirm``.
        """
        if not self.env.context.get("bypass_risk", False):
            for order in self.filtered(
                lambda so: not so.company_id.allow_overrisk_sale_confirmation
            ):
                partner = order.partner_invoice_id.commercial_partner_id
                exception_msg = order.evaluate_risk_message(partner)
                if exception_msg:
                    return (
                        self.env["partner.risk.exceeded.wiz"]
                        .create(
                            {
                                "exception_msg": exception_msg,
                                "partner_id": partner.id,
                                "origin_reference": f"{order._name},{order.id}",
                                "continue_method": "action_confirm",
                            }
                        )
                        .action_show()
                    )
        return super().action_confirm()
