
Portugal - Issuance Blocking
============================

Allows companies to eventually block fiscal document issuance when the related
partners and/or products are marked as blocked, are archived or are not for
sale (products only).

**Table of contents**

.. contents::
   :local:

Installation
============

Add the module to an addons folder, restart Odoo, update the addons list and activate
it.

Configuration
=============

On the partner form, select a reason on the 'Doc. Issuance Blocking' field on
partners on which you want to activate the issuance blocking. Leave empty to
allow normal issuance.

On the product form, select a reason on the 'Doc. Issuance Blocking' field on
products on which you want to activate the issuance blocking. Leave empty to
allow normal issuance.

On the Portuguese Invoicing section of the Accounting settings, find the Doc.
Issuance Blocking sub-section and activate the Partners/Products checkbox to
start blocking fiscal document issuance on partners and products that are
marked as such.

If you want to apply the blocking mechanism to archived products and/or
partners, select the Block Archived checkbox. If you set the 'Block products
that are not for sale' checkbox, a similar blocking will be effective on
products that don't have the 'Can be Sold' option selected.

Usage
=====

Try to validate a fiscal document (eg. Invoice, Receipt, Waybill, Quotation,
etc.). If it contains a partner or a product with an active Doc. Issuance
Blocking reason or in an archived state (depending on your configuration),
you won't be allowed to validate it.

Changelog
=========

1.0.1 (2023-12-04)
~~~~~~~~~~~~~~~~~~~

**Features**

- Added blocking on products on which the 'Can be Sold' property is false.

1.0.0 (2023-11-21)
~~~~~~~~~~~~~~~~~~~

**Features**

- Initial changelog

Credits
=======

Authors
~~~~~~~

* Exo Software, Lda.

Contributors
~~~~~~~~~~~~

* `Exo Software <https://exosoftware.pt>`_:

  * Pedro Castro Silva
  * André Leite
  * João Costa

Maintainers
~~~~~~~~~~~

This module is maintained by Exo Software, Lda.

.. image:: https://exosoftware.pt/logo.png
   :alt: Exo Software
   :target: https://exosoftware.pt
   :width: 100px
