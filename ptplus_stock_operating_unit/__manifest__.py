# Copyright 2019 Exo Software, Lda.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "Portugal - Stock with Operating Units",
    "version": "17.0.4.0.0",
    "author": "Exo Software, " "Odoo Community Association (OCA)",
    "website": "https://exosoftware.pt",
    "license": "LGPL-3",
    "category": "Localization",
    "depends": [
        "ptplus_stock",
        "stock_operating_unit",
    ],
    "data": [
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
