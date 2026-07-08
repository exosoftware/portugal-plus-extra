=========================
Portugal - Credit Control
=========================

This module bridges the OCA financial risk apps (`account_financial_risk`,
`sale_financial_risk`) with the Portuguese localization (`ptplus_sale`).

Problem
=======

When confirming a sale order, `ptplus_sale` performs irreversible fiscal work
inside its own `action_confirm` -- it archives a copy of the quotation, changes
the document type from OR (quotation) to NE (order) and issues the document
(serial numbering + hash signing) -- **before** calling `super()`.

The OCA `sale_financial_risk` credit gate lives further down the `super()`
chain and, when the customer's credit limit is exceeded, *returns* a wizard
action instead of raising an exception. As a result the base confirmation never
runs (the order stays in the `sent` state) but the transaction still commits,
persisting the partial PT+ work. The order is left as a fully issued NE stuck in
`sent`, plus a spurious quotation copy, and any retry fails with a duplicate
document number. Clicking "Cancel" on the wizard cannot undo it, because the
transaction has already been committed.

Because `ptplus_sale` and `sale_financial_risk` do not depend on each other,
the order in which their `action_confirm` overrides run is not guaranteed --
this affects any deployment that combines the Portuguese localization with the
OCA credit control.

Solution
========

This module depends on both `ptplus_sale` and `sale_financial_risk`, so its
`action_confirm` override is the most derived one and runs first. It replays the
exact OCA risk gate *before* `super()` -- and therefore before any fiscal
operation. When the risk is exceeded the same wizard is shown without PT+ ever
touching the document; otherwise confirmation proceeds normally. The wizard's
"Continue" button keeps working through the standard `bypass_risk` context.

Installation
============

Installed automatically whenever both `ptplus_sale` and `sale_financial_risk`
are present.

Credits
=======

Contributors
~~~~~~~~~~~~~

* Exo Software <https://exosoftware.pt>
