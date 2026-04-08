##############################################################################
#
#   Copyright (C) 2016 Exo Software, Lda. (<https://exo.pt>)
#
##############################################################################
# pylint: disable=license-allowed, manifest-required-author

{
    "name": "Portugal - Invoice grouped by picking",
    "version": "19.0.1.1.0",
    "license": "LGPL-3",
    "depends": ["account_invoice_report_grouped_by_picking", "ptplus_stock"],
    "author": "EXO Software",
    "website": "https://exosoftware.pt",
    "category": "Extra Tools",
    "data": [
        "views/report_invoice.xml",
    ],
    "installable": False,
    "auto_install": True,
    "application": False,
}
