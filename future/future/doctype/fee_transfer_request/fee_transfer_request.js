frappe.ui.form.on("Fee Transfer Request", {
	setup(frm) {
		frm.set_query("from_enrollment", () => ({ filters: { docstatus: 1 } }));
		frm.set_query("to_enrollment", () => ({ filters: { docstatus: 1, name: ["!=", frm.doc.from_enrollment || ""] } }));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			const approver = frappe.user.has_role(["System Manager", "Sales Manager", "Accounts Manager"]);
			frm.set_intro(
				approver ? __("Check the amounts, then submit to approve the transfer.") : __("Waiting for a manager to approve (submit) this transfer."),
				"orange"
			);
		}
	},
	from_enrollment: show_available,
	from_category: show_available,
});

function show_available(frm) {
	if (!frm.doc.from_enrollment || !frm.doc.from_category) return;
	frappe
		.xcall("future.admissions.get_available", { enrollment: frm.doc.from_enrollment, category: frm.doc.from_category })
		.then((v) => frm.set_value("available", v));
}
