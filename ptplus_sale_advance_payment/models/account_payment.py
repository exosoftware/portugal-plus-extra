from odoo import _, api, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("sale_id")
    def _compute_destination_account_id(self):
        res = super()._compute_destination_account_id()
        for pay in self:
            if pay.pt_invoicing() and pay.sale_id and pay.payment_type == "inbound":
                all_category = self.env.ref("product.product_category_all")
                downpayment_acc = all_category.with_company(
                    pay.company_id
                ).property_account_downpayment_categ_id
                if not downpayment_acc:
                    raise UserError(
                        _("Please set a down payment account in the category 'All'")
                    )
                pay.destination_account_id = downpayment_acc
        return res

    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        return res + ("sale_id",)
