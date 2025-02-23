from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    internal_name = fields.Char("Internal Ref.", copy=False, readonly=True)

    _sql_constraints = [
        (
            "internal_name_unique",
            "unique(internal_name, company_id)",
            "Internal Name must be unique per Company.",
        ),
    ]

    def _get_new_rev_data(self, new_rev_number):
        res = super()._get_new_rev_data(new_rev_number)

        res.update({"internal_name": "%s.%02d"
                    % (self.unrevisioned_name, new_rev_number),})
        res.pop("name", None)

        return res

