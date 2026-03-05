import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)  # pylint: disable=C0103


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        compute="_compute_operating_unit_id",
        store=True,
    )

    def _prepare_payment_vals(self, invoices):
        vals = super()._prepare_payment_vals(invoices)
        vals.update(
            {
                "operating_unit_id": self.operating_unit_id,
            }
        )
        return vals

    @api.model
    def _get_line_batch_key(self, line):
        # OVERRIDE to set the operating unit
        vals = super()._get_line_batch_key(line)
        operating_unit_id = (
            line.operating_unit_id and line.operating_unit_id.id or False
        )
        if operating_unit_id:
            vals["operating_unit_id"] = operating_unit_id
        return vals

    @api.depends("line_ids")
    def _compute_from_lines(self):
        # OVERRIDE to set the operating unit. If there's one and only one
        # operating unit in the moves lines, we'll set it up on the payment
        # pylint: disable=missing-return
        super()._compute_from_lines()
        for wizard in self:
            operating_units = []
            for batch in wizard._get_batches():
                operating_units.extend(batch["lines"].mapped("operating_unit_id"))

            _logger.info(operating_units)
            if len(operating_units) == 1:
                wizard.operating_unit_id = operating_units[0]
