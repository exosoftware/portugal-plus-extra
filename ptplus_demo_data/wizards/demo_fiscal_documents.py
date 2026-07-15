##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
from odoo import _, fields, models
from odoo.fields import Command


class PtplusDemoDataWizard(models.TransientModel):
    _inherit = "ptplus.demo.data.wizard"

    def _demo_get_fiscal_doc_type(
        self, company, doc_type, activate=False, sequence_name=None, sequence_code=None
    ):
        """Look up a company's fiscal document type, optionally activating it.

        Several types (e.g. Worksheet/FO, Asset Transport Note/GA) ship
        inactive AND without a sequence_id (see
        ``ptplus_sale``/``ptplus_stock`` ``models/res_company.py``
        ``l10n_pt_create_default_fiscal_doc_types``) since they're optional
        features. ``pt_issue()`` requires a sequence_id to assign a document
        number, so activating one for demo purposes means creating one too.
        """
        fdt = (
            self.env["fiscal.document.type"]
            .with_context(active_test=False)
            .search([("company_id", "=", company.id), ("type", "=", doc_type)], limit=1)
        )
        if not fdt or not activate:
            return fdt
        if not fdt.active:
            fdt.active = True
        if not fdt.sequence_id and sequence_name and sequence_code:
            fdt.sequence_id = company._l10n_pt_create_sequence(
                sequence_name, sequence_code, company
            )
        return fdt

    def _demo_get_default_sale_tax(self, company):
        """The company's standard (non-down-payment) sale VAT tax.

        The PT chart template's own default resolution
        (``res.company.account_sale_tax_id``) picks up a down-payment
        ("(OBS) (Adiantamento)") tax variant instead of the plain standard
        one -- fine for an actual down-payment invoice, wrong on a regular
        order/invoice line. Look up a normal-rate sale VAT tax explicitly
        instead of trusting that field.
        """
        return self.env["account.tax"].search(
            [
                ("company_id", "=", company.id),
                ("type_tax_use", "=", "sale"),
                ("l10n_pt_genre", "=", "IVA"),
                ("pt_vat_tax_type", "=", "NOR"),
                # "ogs" = Other Goods and Services -- the general-purpose
                # rate, as opposed to the "asset"/"stock" variants meant for
                # fixed-asset sales or specific stock movements.
                ("pt_vat_subject", "=", "ogs"),
                ("name", "not ilike", "Adiantamento"),
            ],
            order="amount desc",
            limit=1,
        )

    def _demo_get_or_create_product(
        self, company, name, list_price, is_storable, taxes=None
    ):
        product = self.env["product.template"].search(
            [("name", "=", name), ("company_id", "in", [company.id, False])], limit=1
        )
        if product:
            return product
        vals = {
            "name": name,
            "list_price": list_price,
            "type": "consu",
            "is_storable": is_storable,
            "sale_ok": True,
            "purchase_ok": False,
            "company_id": company.id,
            # Set explicitly rather than relying on the default: it can
            # otherwise pick up extra/wrong-company taxes at create time,
            # which _check_company() later rejects on any invoice line
            # using this product.
            "taxes_id": [
                Command.set(
                    taxes.ids if taxes else self._demo_get_default_sale_tax(company).ids
                )
            ],
        }
        return self.env["product.template"].create(vals)

    def _demo_get_or_create_eco_tax_product(self, company):
        """A product line for the environmental (eco) fee itself.

        l10n_pt_genre='ECO' is what exempts an invoice line from needing a
        separate VAT tax (see pt_check_lines/_pt_check_line_taxes's
        has_pt_genre_product check) -- matching how ptplus/tests/common.py
        sets up its own demo "eco_tax_product".
        """
        name = _("Taxa de Gestão de Resíduos - Equip. Elétrico")
        product = self.env["product.template"].search(
            [("name", "=", name), ("company_id", "in", [company.id, False])], limit=1
        )
        if product:
            return product
        return self.env["product.template"].create(
            {
                "name": name,
                "type": "service",
                "list_price": 1.5,
                "sale_ok": True,
                "purchase_ok": False,
                "company_id": company.id,
                "l10n_pt_genre": "ECO",
                "l10n_pt_eco_tax_type": "electr",
                "taxes_id": [Command.set([])],
            }
        )

    def _demo_internal_transfer_location(self, company):
        # The warehouse itself is created earlier, in
        # _demo_create_warehouse (before the chart of accounts / fiscal
        # document types load), so it always already exists here.
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1
        )
        location = self.env["stock.location"].search(
            [
                ("name", "=", "Equipamento em Obra"),
                ("location_id", "=", warehouse.view_location_id.id),
            ],
            limit=1,
        )
        if not location:
            location = self.env["stock.location"].create(
                {
                    "name": "Equipamento em Obra",
                    "usage": "internal",
                    "location_id": warehouse.view_location_id.id,
                    "company_id": company.id,
                }
            )
        return warehouse, location

    def _demo_get_income_account(self, company):
        """The default revenue account for invoice lines.

        account.move.line's account_id is a precompute field derived from
        the product/its category's income account -- but a demo product
        created without an explicit category default can leave it empty,
        which account_move_line_check_accountable_required_fields rejects.
        ptplus's own test base (ptplus/tests/common.py) sidesteps this the
        same way: it always sets account_id explicitly rather than relying
        on the compute.
        """
        # account.account is shared across companies via company_ids (m2m)
        # since Odoo 17 -- there's no plain company_id field to filter on.
        return self.env["account.account"].search(
            [("company_ids", "in", company.id), ("account_type", "=", "income")],
            limit=1,
        )

    def _demo_validate_picking(self, picking):
        picking.action_confirm()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        # ptplus_stock's pt_issue() reports transport documents to the AT
        # webservice ("Comunicação de Guias de Transporte") unless a
        # delivery code is already present -- pre-filling it (as if it had
        # already been communicated) skips that live call, which would
        # otherwise fail with no real AT credentials configured.
        picking.l10n_pt_delivery_code = "DEMO-%s" % picking.id
        picking.button_validate()

    def _demo_generate_fiscal_documents(self, company, partner):
        log = []
        service = self._demo_get_or_create_product(
            company, _("Serviços de Consultoria Técnica"), 850.0, False
        )
        material = self._demo_get_or_create_product(
            company, _("Materiais de Construção"), 120.0, True
        )
        equipment = self._demo_get_or_create_product(
            company, _("Equipamento Elétrico"), 300.0, True
        )

        # Orçamento (OR) - draft quotation
        quotation = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": service.product_variant_id.id,
                            "product_uom_qty": 1,
                        }
                    )
                ],
            }
        )
        quotation.pt_issue()
        log.append(_("Orçamento (OR) criado: %s") % quotation.name)

        # Nota de Encomenda (NE) - direct confirmed order
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": material.product_variant_id.id,
                            "product_uom_qty": 10,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        log.append(_("Nota de Encomenda (NE) criada: %s") % order.name)

        # Worksheet (FO) - orçamento explicitly tagged as Worksheet
        fo_type = self._demo_get_fiscal_doc_type(
            company,
            "FO",
            activate=True,
            sequence_name=_("Folhas de Obra"),
            sequence_code="pt.sale.worksheet",
        )
        worksheet = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": company.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": service.product_variant_id.id,
                            "product_uom_qty": 8,
                        }
                    )
                ],
            }
        )
        if fo_type:
            worksheet.fiscal_document_type_id = fo_type
        worksheet.pt_issue()
        log.append(_("Worksheet (FO) criado: %s") % worksheet.name)

        # Guia de Remessa (GR) - delivery of the confirmed order
        delivery = order.picking_ids.filtered(lambda p: p.state != "done")
        if delivery:
            self._demo_validate_picking(delivery[0])
            log.append(_("Guia de Remessa (GR) criada: %s") % delivery[0].name)

        # Guia de Ativos Próprios (GA) - internal transfer of own equipment
        self._demo_get_fiscal_doc_type(
            company,
            "GA",
            activate=True,
            sequence_name=_("Guias de Ativos Próprios"),
            sequence_code="pt.deliveryslip.asset",
        )
        warehouse, jobsite_location = self._demo_internal_transfer_location(company)
        internal_picking = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.int_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": jobsite_location.id,
                "company_id": company.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": equipment.product_variant_id.id,
                            "product_uom_qty": 2,
                            "product_uom": equipment.uom_id.id,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": jobsite_location.id,
                            "company_id": company.id,
                        }
                    )
                ],
            }
        )
        self._demo_validate_picking(internal_picking)
        log.append(_("Guia de Ativos Próprios (GA) criada: %s") % internal_picking.name)

        # Fatura (FT) + Pagamento (RG)
        income_account = self._demo_get_income_account(company)
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "company_id": company.id,
                "invoice_date": fields.Date.context_today(self),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": service.product_variant_id.id,
                            "quantity": 2,
                            "price_unit": 500.0,
                            "account_id": income_account.id,
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        log.append(_("Fatura (FT) criada: %s") % invoice.name)

        payment_wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({})
        )
        payment_wizard.action_create_payments()
        log.append(_("Pagamento (RG) registado para a fatura %s") % invoice.name)

        # Fatura com Eco Taxa: the eco fee is its own line, on a product
        # marked l10n_pt_genre='ECO' -- that's what PT+ actually requires
        # (ptplus/tests/common.py's demo "eco_tax_product" does the same);
        # a %/fixed account.tax attached to a normal product doesn't carry
        # a VAT genre, and pt_check_lines() rejects any line with no VAT tax
        # unless the line's product itself is genre-classified.
        eco_tax_product = self._demo_get_or_create_eco_tax_product(company)
        eco_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "company_id": company.id,
                "invoice_date": fields.Date.context_today(self),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": equipment.product_variant_id.id,
                            "quantity": 3,
                            "price_unit": 300.0,
                            "account_id": income_account.id,
                            "tax_ids": [Command.set(equipment.taxes_id.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": eco_tax_product.product_variant_id.id,
                            "quantity": 3,
                            "price_unit": eco_tax_product.list_price,
                            "account_id": income_account.id,
                            "tax_ids": [Command.set([])],
                        }
                    ),
                ],
            }
        )
        eco_invoice.action_post()
        log.append(_("Fatura com Eco Taxa criada: %s") % eco_invoice.name)

        return log
