from odoo import _, api, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("sale_id")
    def _compute_destination_account_id(self):
        res = super()._compute_destination_account_id()
        for pay in self:
            if pay.pt_invoicing() and pay.sale_id and pay.payment_type == "inbound":
                product_id = pay.company_id.with_company(
                    pay.company_id
                ).sale_down_payment_product_id
                if not product_id:
                    raise UserError(
                        _(
                            "Please set a down payment product in the Sales configuration"
                        )
                    )
                pay.destination_account_id = product_id.property_account_income_id
        return res

    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ("sale_id",)
