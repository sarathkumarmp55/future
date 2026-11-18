frappe.ui.form.on("Consultant Fee Run", {
	setup(frm) {
		if (frm.is_new() && !frm.doc.company) frm.set_value("company", frappe.defaults.get_default("company"));
	},
	refresh(frm) {
		if (frm.doc.docstatus !== 0) return;
		frm.add_custom_button(__("Get Consultants"), () => {
			if (!frm.doc.fee_month) return frappe.msgprint(__("Choose the fee month first."));
			frm.call("get_consultants").then(() => {
				frm.refresh_fields();
				frm.dirty();
			});
		});
		frm.set_intro(
			__("Save to work out the fees from attendance. Submit to create a draft Purchase Invoice for each consultant."),
			"blue"
		);
	},
});

frappe.ui.form.on("Consultant Fee Run Item", {
	off_days(frm) {
		// Figures are worked out on the server; saving shows the new fee.
		frm.dirty();
	},
});
