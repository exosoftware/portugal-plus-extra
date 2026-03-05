# Copyright 2021 Exo Software, Lda. (http://exo.pt)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Partner Statement Send by Email",
    "version": "19.0.1.0.1",
    "license": "AGPL-3",
    "author": "Exo Software, Odoo Community Association (OCA)",
    "website": "https://exosoftware.pt",
    "category": "Accounting & Finance",
    "depends": [
        "partner_statement",
    ],
    "data": [
        "data/partner_mail.xml",
        "wizards/statement_wizard_views.xml",
    ],
    "installable": False,
    "application": False,
}
