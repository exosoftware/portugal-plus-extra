import logging

from odoo import api, models
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)  # pylint: disable=C0103


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def lines_grouped_contains_returns(self, lines_grouped):
        for gl in lines_grouped:
            line = gl.get("line")
            picking = gl.get("picking")
            if not line or not picking:
                continue

            uom = line.product_uom_id
            precision_rounding = uom.rounding if uom else 0.01

            if (
                float_compare(
                    gl.get("quantity", 0.0),
                    gl.get("quantity_invoiced", gl.get("quantity", 0.0)),
                    precision_rounding=precision_rounding,
                )
                != 0
            ):
                return True
        return False

    def _ptplus_get_returned_moves(self, stock_move):
        returned = stock_move.returned_move_ids
        origin = stock_move.origin_returned_move_id
        if origin:
            returned |= origin
        return returned

    def _ptplus_move_matches_invoice_line(self, stock_move, invoice_line):
        if stock_move.invoice_line_ids:
            return invoice_line in stock_move.invoice_line_ids
        return False

    def lines_grouped_by_picking(self):
        grouped_lines = super().lines_grouped_by_picking()

        for gl in grouped_lines:
            gl["quantity_invoiced"] = gl.get("quantity", 0.0)

            picking = gl.get("picking")
            line = gl.get("line")

            if not picking or not line:
                continue

            inverse_qty_total = 0.0

            picking_moves = picking.move_ids_without_package
            if not picking_moves:
                continue

            for move in picking_moves:
                returned_moves = self._ptplus_get_returned_moves(move)
                if not returned_moves:
                    continue

                returned_qty_for_line = 0.0
                for rmove in returned_moves:
                    if self._ptplus_move_matches_invoice_line(rmove, line):
                        returned_qty_for_line += rmove.quantity

                move_done_qty = rmove.quantity
                inverse_qty_total += min(returned_qty_for_line, move_done_qty)

            qty = gl.get("quantity", 0.0)
            sign = 1.0
            if qty:
                sign = qty / abs(qty)

            gl["quantity_invoiced"] = qty - inverse_qty_total * sign

        return grouped_lines
