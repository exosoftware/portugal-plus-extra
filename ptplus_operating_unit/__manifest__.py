# Copyright 2019 Exo Software, Lda.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "Portugal - Accounting with Operating Units",
    "version": "17.0.4.0.0",
    "author": "Exo Software, " "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "license": "LGPL-3",
    "category": "Localization",
    "depends": [
        "ptplus",
        "account_operating_unit",
    ],
    "data": [
        "security/security.xml",
        "views/fiscal_document_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "wizards/account_payment_register_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
