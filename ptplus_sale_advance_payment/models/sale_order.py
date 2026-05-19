from odoo import fields, models
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _compute_advance_payment(self):
        """Recognise PT advance payments posted to the down payment account.

        The base ``sale_advance_payment`` module only counts advance payment
        move lines whose account type is ``asset_receivable``. This module
        (see ``account_payment.py``) redirects PT inbound advance payments to
        the category down payment account, which by definition is *never* a
        receivable account. As a result those payments are invisible to the
        base computation and ``amount_residual`` is never reduced.

        This override re-runs the base computation and additionally subtracts
        the advance amount still sitting on the down payment account.
        """
        res = super()._compute_advance_payment()
        category = self.env.ref(
            "product.product_category_all", raise_if_not_found=False
        )
        if not category:
            return res
        for order in self:
            downpayment_acc = category.with_company(
                order.company_id
            ).property_account_downpayment_categ_id
            if not downpayment_acc:
                continue
            advance_lines = order.account_payment_ids.move_id.line_ids.filtered(
                lambda aml: aml.account_id == downpayment_acc
                and aml.parent_state == "posted"
            )
            if not advance_lines:
                continue
            # Surface the down payment lines alongside the receivable ones.
            order.payment_line_ids |= advance_lines

            advance_amount = 0.0
            for line in advance_lines:
                line_currency = line.currency_id or line.company_id.currency_id
                # When the down payment account is reconcilable we use the
                # residual amount, so that once the line is reconciled (e.g.
                # by the regularization move) it stops being counted here and
                # is instead reflected through the related invoice residual.
                # Otherwise the residual is meaningless and we fall back to
                # the full posted amount.
                if downpayment_acc.reconcile:
                    line_amount = (
                        line.amount_residual_currency
                        if line.currency_id
                        else line.amount_residual
                    )
                else:
                    line_amount = (
                        line.amount_currency if line.currency_id else line.balance
                    )
                # Inbound payments credit the down payment account: invert the
                # sign so the advance is expressed as a positive amount.
                line_amount *= -1
                if line_currency != order.currency_id:
                    advance_amount += line.currency_id._convert(
                        line_amount,
                        order.currency_id,
                        order.company_id,
                        line.date or fields.Date.today(),
                    )
                else:
                    advance_amount += line_amount

            if order.currency_id.is_zero(advance_amount):
                continue
            order.amount_residual -= advance_amount
            has_due_amount = float_compare(
                order.amount_residual,
                0.0,
                precision_rounding=order.currency_id.rounding,
            )
            order.advance_payment_status = "paid" if has_due_amount <= 0 else "partial"
        return res
