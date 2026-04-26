from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_pt_revision_name = fields.Char("Revision Name", copy=False, readonly=True)

    # When we have a quotation, and want to confirm it, it is copied,
    # creating a document with the same name, company and document series,
    # triggering this constraint. Since the name is controlled by the module only,
    # we will be removing this constraint for now.
    # _l10n_pt_revision_name_unique = models.Constraint(
    #     "UNIQUE (l10n_pt_revision_name, company_id, fiscal_document_type_id)",
    #     "Revision Name must be unique per Company and Document Series.",
    # )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if (
                not record.old_revision_ids
                and not record.l10n_pt_revision_name
                and record.country_code == "PT"
            ):
                record.l10n_pt_revision_name = (
                    record.l10n_pt_order_id.l10n_pt_revision_name or record.name
                )
        return records

    def _get_new_rev_data(self, new_rev_number):
        res = super()._get_new_rev_data(new_rev_number)
        if self.country_code != "PT":
            return res

        revision_name = "%s.%02d" % (self.unrevisioned_name, new_rev_number)
        res.update(
            {
                "l10n_pt_revision_name": revision_name,
                "name": revision_name,
            }
        )

        return res

    def create_revision(self):
        if self.country_code != "PT":
            return super().create_revision()

        return {
            "type": "ir.actions.act_window",
            "name": _("New Order"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "wizard.order.revision",
            "target": "new",
            "context": {"default_order_id": self.id},
        }

    def pt_get_fullname(self, lang=False):
        if not self.l10n_pt_revision_name:
            # Let super handle it
            return super(SaleOrder, self).pt_get_fullname(lang)

        # New revision name
        return "{} {}".format(self.pt_get_type_name(lang), self.l10n_pt_revision_name)
