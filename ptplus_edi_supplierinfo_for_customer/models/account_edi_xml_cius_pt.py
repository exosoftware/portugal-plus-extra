import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountEdiXmlCiusPt(models.AbstractModel):
    _inherit = "account.edi.xml.cius_pt_211"

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        """EXTENDS account.edi.xml.ubl_20"""
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)

        # Customer identifier of the product.
        vals["buyers_item_identification_vals"] = {"id": line.product_customer_code}
        return vals
