from odoo import Command, _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        res = super()._post(soft)

        for move in res:
            if not move.pt_invoicing():
                continue
            sale_orders = move.line_ids.sale_line_ids.order_id
            payments = sale_orders.account_payment_ids.filtered(
                lambda pay: pay.move_id.state == "posted"
            )
            print(sale_orders, payments)
            if not sale_orders or not payments:
                continue
            advance_amount = 0.0
            for pay in payments:
                advance_amount += pay.currency_id._convert(
                    pay.amount,
                    move.currency_id,
                    move.company_id,
                    move.date or move.invoice_date,
                )

            debit_account_id = move.company_id.downpayment_account_id
            if not debit_account_id:
                raise UserError(
                    _("Please set a down payment account in the Sales settings.")
                )

            credit_account_id = move.partner_id.with_company(
                move.company_id
            ).property_account_receivable_id

            line_ids = [
                Command.create(
                    {
                        "name": _("Downpayments"),
                        "date_maturity": move.date or move.invoice_date,
                        "amount_currency": advance_amount,
                        "currency_id": move.currency_id.id,
                        "debit": advance_amount,
                        "partner_id": move.partner_id.id,
                        "account_id": debit_account_id.id,
                    }
                ),
                Command.create(
                    {
                        "name": _("Downpayments"),
                        "date_maturity": move.date or move.invoice_date,
                        "amount_currency": -advance_amount,
                        "currency_id": move.currency_id.id,
                        "credit": advance_amount,
                        "partner_id": move.partner_id.id,
                        "account_id": credit_account_id.id,
                    }
                ),
            ]

            reg_move = self.with_company(move.company_id).create(
                {
                    "move_type": "entry",
                    "company_id": move.company_id.id,
                    "partner_id": move.partner_id.id,
                    "ref": _(
                        "Regularization of down payments: %s",
                        ", ".join(payments.mapped("name")),
                    ),
                    "line_ids": line_ids,
                }
            )
            reg_move._post()

            move.message_post(
                body=_(
                    "A regularization move has been created automatically "
                    "to cover the down payments: %s",
                    reg_move._get_html_link(),
                )
            )

        return res
