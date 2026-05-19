from odoo import _, api, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("journal_id", "partner_id", "partner_type", "sale_id")
    def _compute_destination_account_id(self):
        res = super()._compute_destination_account_id()
        for pay in self:
            if pay.pt_invoicing() and pay.sale_id and pay.payment_type == "inbound":
                downpayment_acc = pay.company_id.downpayment_account_id
                if not downpayment_acc:
                    raise UserError(
                        _("Please set a down payment account in the Sales settings.")
                    )
                if not downpayment_acc.reconcile:
                    raise UserError(
                        _(
                            "The down payment account '%s' must allow "
                            "reconciliation so advance payments can be applied "
                            "to invoices.",
                            downpayment_acc.display_name,
                        )
                    )
                pay.destination_account_id = downpayment_acc
        return res

    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ("sale_id",)
