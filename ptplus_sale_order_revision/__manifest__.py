# Copyright 2025 Exo Software, Lda. (<https://exosoftware.pt>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "Portugal - Sale Order Revision",
    "version": "18.0.1.0.0",
    "category": "Sale Management",
    "author": "Exo Software",
    "website": "https://exosoftware.pt",
    "license": "AGPL-3",
    "category": "Localization",
    "depends": [
        "sale_order_revision",
        "ptplus_sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/report_sale_order.xml",
        "wizard/wizard_order_revision.xml",
    ],
    "demo": [],
    "installable": True,
}
