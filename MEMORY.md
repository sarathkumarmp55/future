# future app

- Site: `future.com` (bench at `/home/user/frappe-benchA15`, apps install via `sites/apps.txt`; future not yet in apps.txt, list via `bench --site future.com list-apps` shows it installed).
- Wire Program doctype JS via `doctype_js` in `future/hooks.py` -> `public/js/program.js`.
- Program doctype custom fields: child table `custom_fees_details` (Table -> "Fees Details") with `component`+`amount`, and Currency `custom_total_amount`. Sum of child `amount` is written to `custom_total_amount` from `public/js/program.js`.
- Child table removal event name is `<child_field>_remove`, i.e. `custom_fees_details_remove`.
