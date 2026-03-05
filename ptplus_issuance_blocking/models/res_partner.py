##############################################################################
#
#    Copyright (C) 2016 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_pt_issuance_blocking = fields.Selection(
        string="Doc. Issuance Blocking",
        selection=[
            ("review", "Needs Review"),
            ("obsolete", "Obsolete"),
        ],
        help="Choose a reason to block fiscal document issuance for this partner "
        "or leave blank to keep it unrestrained.",
    )
