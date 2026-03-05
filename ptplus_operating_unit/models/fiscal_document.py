# Copyright 2019 Exo Software Lda.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class FiscalDocumentType(models.Model):
    _inherit = "fiscal.document.type"

    operating_unit_id = fields.Many2one(
        "operating.unit",
        "Operating Unit",
    )
