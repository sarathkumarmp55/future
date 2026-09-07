// Copyright (c) 2026, sarath and contributors
// For license information, please see license.txt

frappe.ui.form.on("Discount Approval Log", {
	before_submit(frm) {
        if (frm.doc.discount_status === "Pending") {
            frappe.throw(
                __("Cannot submit because Discount Status is Pending.")
            );
        }
    }
});
