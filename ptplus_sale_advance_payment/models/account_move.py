from odoo import Command, _, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        res = super()._post(soft)
        if not self.pt_invoicing():
            return res

        for move in self:
            sale_orders = move.line_ids.sale_line_ids.order_id
            if not sale_orders:
                continue
            payments = sale_orders.account_payment_ids.filtered(
                lambda pay: pay.state == "posted"
            )
            advance_amount = 0.0
            for pay in payments:
                advance_amount += pay.currency_id._convert(
                    pay.amount,
                    self.currency_id,
                    self.company_id,
                    self.date or self.invoice_date,
                )

            debit_account_id = self.company_id.with_company(
                pay.company_id
            ).sale_down_payment_product_id.property_account_income_id

            credit_account_id = self.partner_id.with_company(
                self.company_id
            ).property_account_receivable_id

            line_ids = [
                Command.create(
                    {
                        "name": _("Downpayments"),
                        "date_maturity": self.date or self.invoice_date,
                        "amount_currency": advance_amount,
                        "currency_id": self.currency_id.id,
                        "debit": advance_amount,
                        "partner_id": self.partner_id.id,
                        "account_id": debit_account_id.id,
                    }
                ),
                Command.create(
                    {
                        "name": _("Downpayments"),
                        "date_maturity": self.date or self.invoice_date,
                        "amount_currency": -advance_amount,
                        "currency_id": self.currency_id.id,
                        "credit": advance_amount,
                        "partner_id": self.partner_id.id,
                        "account_id": credit_account_id.id,
                    }
                ),
            ]

            reg_move = self.create(
                {
                    "move_type": "entry",
                    "partner_id": self.partner_id.id,
                    "ref": _("Regularization of down payments: {names}").format(
                        names=", ".join(payments.mapped("name"))
                    ),
                    "line_ids": line_ids,
                }
            )
            reg_move._post()

            move.message_post(
                body=_(
                    "A regularization move has been created automatically "
                    "to cover the down payments: {link}"
                ).format(link=reg_move._get_html_link())
            )

        return res
