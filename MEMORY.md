# future app

- Site: `future.com` (bench at `/home/user/frappe-benchA15`, apps install via `sites/apps.txt`; future not yet in apps.txt, list via `bench --site future.com list-apps` shows it installed).
- Wire Program doctype JS via `doctype_js` in `future/hooks.py` -> `public/js/program.js`.
- Program doctype custom fields: child table `custom_fees_details` (Table -> "Fees Details") with `component`+`amount`, and Currency `custom_total_amount`. Sum of child `amount` is written to `custom_total_amount` from `public/js/program.js`.
- Child table removal event name is `<child_field>_remove`, i.e. `custom_fees_details_remove`.
- `Payment Approval Log.on_submit` builds the Sales Invoice programmatically (both `from_opportunity` and `from_student_service` paths). Item tax templates (e.g. Orientation Fee -> "18 - F" @ 18%) are NOT auto-applied on programmatic `insert()`; must call `invoice.set_missing_values()` + `invoice.append_taxes_from_item_tax_template()` (after setting `invoice.company`) to populate `item_tax_template`/`item_tax_rate` and the `taxes` table. `add_taxes_from_item_tax_template` is enabled in Accounts Settings, so the JS-side behavior is mirrored this way server-side.
- Fee `received_amount` is treated as GST-INCLUSIVE. Mark the appended tax rows `tax.included_in_print_rate = 1` so ERPNext back-calculates net + tax from the gross rate (avoids the 1-paise drift of manually dividing `received_amount / 1.18`, which produced grand_total=4000.01 vs outstanding=4000.00 and the "Allocated Amount cannot be greater than outstanding amount" error).
- The Payment Entry must allocate `invoice.outstanding_amount` (not `invoice.grand_total`, which can differ by rounding) and use `invoice.grand_total` for `paid_amount`/`received_amount` so the invoice fully settles.
