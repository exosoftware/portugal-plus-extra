##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
# pylint: disable=license-allowed, manifest-required-author

{
    "name": "Portugal - Demo Data Generator",
    "version": "19.0.1.0.0",
    "license": "OPL-1",
    "author": "Exo Software",
    "website": "https://exosoftware.pt",
    "category": "Extra Tools",
    "summary": "Populate a company with cross-app demo data for PT+ presentations",
    "depends": [
        "ptplus",
        "ptplus_sale",
        "ptplus_stock",
        "crm",
        "voip",
        "sale_management",
        "sale_project",
        "hr_timesheet",
        "planning",
        "project_forecast",
        "sale_project_forecast",
        "documents_project",
        "hr_payroll",
        "mass_mailing_sms",
        "marketing_automation",
        "whatsapp",
        "helpdesk",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/ptplus_demo_data_wizard_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
