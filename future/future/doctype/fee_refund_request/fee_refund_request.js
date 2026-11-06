frappe.ui.form.on("Fee Refund Request", {
	setup(frm) {
		frm.set_query("enrollment", () => ({ filters: { docstatus: 1 } }));
		frm.set_query("paid_from", () => ({ filters: { account_type: ["in", ["Cash", "Bank"]], is_group: 0 } }));
	},
	refresh(frm) {
		const approver = frappe.user.has_role(["System Manager", "Sales Manager", "Accounts Manager"]);
		const colors = { Requested: "orange", Approved: "blue", Rejected: "red", Paid: "green", Cancelled: "gray" };
		if (!frm.is_new()) frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status] || "gray");
		if (frm.doc.docstatus === 0 && frm.doc.status === "Requested" && !frm.is_new() && approver) {
			frm.add_custom_button(__("Approve"), () =>
				frappe.xcall("future.future.doctype.fee_refund_request.fee_refund_request.approve", { name: frm.doc.name }).then(() => frm.reload_doc())
			).addClass("btn-primary");
			frm.add_custom_button(__("Reject"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }, (v) =>
					frappe.xcall("future.future.doctype.fee_refund_request.fee_refund_request.reject", { name: frm.doc.name, reason: v.reason }).then(() => frm.reload_doc())
				, __("Reject refund"), __("Reject"))
			);
		}
		if (frm.doc.docstatus === 0 && frm.doc.status === "Approved") {
			frm.set_intro(__("Approved. Enter how the refund was paid, then submit to post the payment."), "blue");
		}
		if (frm.doc.status === "Rejected") frm.set_intro(__("Rejected: {0}", [frm.doc.reject_reason || ""]), "red");
	},
	enrollment: show_available,
	category: show_available,
});

function show_available(frm) {
	if (!frm.doc.enrollment || !frm.doc.category) return;
	frappe
		.xcall("future.admissions.get_available", { enrollment: frm.doc.enrollment, category: frm.doc.category })
		.then((v) => frm.set_value("available", v));
}
