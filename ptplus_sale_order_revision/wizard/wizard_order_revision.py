from odoo import _, api, fields, models


class WizardOrderRevision(models.TransientModel):
    _name = "wizard.order.revision"
    _description = "Wizard Order Revision"

    order_id = fields.Many2one("sale.order")
    chatter = fields.Boolean(default=True, help="Copy chatter")
    spreadsheets = fields.Boolean(default=True, help="Copy spreadsheets")
    has_spreadsheets = fields.Boolean(compute="_compute_has_spreadsheets")
    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        related="order_id.invoice_ids",
    )
    invoices = fields.Boolean(
        string="Copy Invoices", default=True, help="Copy invoices."
    )

    @api.depends("order_id")
    def _compute_has_spreadsheets(self):
        for wizard in self:
            order = wizard.order_id
            wizard.has_spreadsheets = bool(
                "spreadsheet_ids" in order._fields and order.spreadsheet_ids
            )

    def pt_create_revision(self):
        self.ensure_one()

        rec = self.order_id
        copied_rec = rec.copy_revision_with_context()

        if self.chatter:
            # Added messages in chatter
            messages = self.env["mail.message"].search(
                [("model", "=", "sale.order"), ("res_id", "=", rec.id)], order="id asc"
            )
            for message in messages:
                message.copy(
                    {
                        "res_id": copied_rec.id,
                        "model": "sale.order",
                    }
                )

            # Added attachments
            attachments = self.env["ir.attachment"].search(
                [("res_model", "=", "sale.order"), ("res_id", "=", rec.id)]
            )
            for attachment in attachments:
                attachment.copy({"res_id": copied_rec.id, "res_model": "sale.order"})

        if self.invoices:
            for invoice in rec.invoice_ids:
                invoice.write({"invoice_origin": copied_rec.name})
                for line in invoice.invoice_line_ids:
                    line.write({"sale_line_ids": [(6, 0, copied_rec.order_line.ids)]})

        # duplicate the spreadsheet
        if (
            self.spreadsheets
            and "spreadsheet_ids" in rec._fields
            and rec.spreadsheet_ids
            and not copied_rec.spreadsheet_ids
        ):
            copied_rec.spreadsheet_ids = rec.spreadsheet_ids.copy(
                {"order_id": copied_rec.id}
            )

        msg = _("New revision created: %s") % copied_rec.l10n_pt_revision_name
        copied_rec.message_post(body=msg)
        rec.message_post(body=msg)

        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "name": _("New Revisions"),
            "res_model": "sale.order",
            "res_id": copied_rec.id,
            "target": "current",
        }
        return action
