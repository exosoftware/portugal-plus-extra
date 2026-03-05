##############################################################################
#
#    Copyright (C) 2016 Exo Software, Lda. (<https://exosoftware.pt>)
#
###########################################################################
from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class FiscalDocument(models.AbstractModel):
    _inherit = "fiscal.document"

    def pt_check_header(self):
        """Raise an error if the doc. contains a blocked or archived partner"""
        self.ensure_one()

        # Check if partner is blocked by the blocking field ...
        partner = self.partner_id and self.partner_id.commercial_partner_id
        if (
            self.company_id.l10n_pt_issuance_blocking
            and partner
            and partner.l10n_pt_issuance_blocking
        ):
            raise UserError(
                _("Can't issue document. Partner '{}' is blocked.").format(partner.name)
            )

        # ... or because it's archived
        if (
            self.company_id.l10n_pt_issuance_blocking_archived
            and partner
            and not partner.active
        ):
            raise UserError(
                _("Can't issue document. Partner '{}' is archived.").format(
                    partner.name
                )
            )

        return super().pt_check_header()

    def pt_check_lines(self):
        """Raise an error if the doc. contains a blocked or archived product"""

        if (
            not self.company_id.l10n_pt_issuance_blocking
            or not self.company_id.l10n_pt_issuance_blocking_archived
        ):
            return super().pt_check_lines()

        # Collect products from document lines
        products = self.env["product.product"]
        if self._name == "account.move":
            products = self.mapped("invoice_line_ids.product_id.product_tmpl_id")
        elif self._name == "sale.order":
            products = self.mapped("order_line.product_id.product_tmpl_id")
        elif self._name == "stock.picking":
            products = self.mapped("move_ids.product_id.product_tmpl_id")

        # Check if one of the products is blocked by the blocking field ...
        blocked = products.filtered(lambda r: r.l10n_pt_issuance_blocking)
        if self.company_id.l10n_pt_issuance_blocking and blocked and blocked[0]:
            raise UserError(
                _("Can't issue document. Product '{}' is blocked.").format(
                    blocked[0].name
                )
            )

        # ... or because it's archived
        archived = products.filtered(lambda r: not r.active)
        if (
            self.company_id.l10n_pt_issuance_blocking_archived
            and archived
            and archived[0]
        ):
            raise UserError(
                _("Can't issue document. Product '{}' is archived.").format(
                    archived[0].name
                )
            )

        sale_not_ok = products.filtered(lambda r: not r.sale_ok)
        if (
            self.company_id.l10n_pt_issuance_blocking_archived
            and sale_not_ok
            and sale_not_ok[0]
        ):
            raise UserError(
                _("Can't issue document. Product '{}' is not for sale.").format(
                    sale_not_ok[0].name
                )
            )

        return super().pt_check_lines()
