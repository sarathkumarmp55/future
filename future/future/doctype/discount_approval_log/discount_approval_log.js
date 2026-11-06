// Discount Approval Log: Approve / Reject for managers (submits the log).
const DAL = "future.future.doctype.discount_approval_log.discount_approval_log";

frappe.ui.form.on("Discount Approval Log", {
	refresh(frm) {
		const colors = { Pending: "orange", Approved: "green", Rejected: "red" };
		if (!frm.is_new()) frm.page.set_indicator(__(frm.doc.discount_status || "Pending"), colors[frm.doc.discount_status] || "gray");
		const approver = frappe.user.has_role(["System Manager", "Sales Manager", "Accounts Manager"]);
		if (frm.doc.docstatus === 0 && frm.doc.discount_status === "Pending" && !frm.is_new() && approver) {
			frm.add_custom_button(__("Approve"), () =>
				frappe.confirm(__("Approve a discount of {0}?", [format_currency(frm.doc.amount)]), () =>
					frappe.xcall(`${DAL}.approve`, { name: frm.doc.name }).then(() => frm.reload_doc())
				)
			).addClass("btn-primary");
			frm.add_custom_button(__("Reject"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }, (v) =>
					frappe.xcall(`${DAL}.reject`, { name: frm.doc.name, reason: v.reason }).then(() => frm.reload_doc())
				, __("Reject discount"), __("Reject"))
			);
		}
	},
	before_submit(frm) {
		if (frm.doc.discount_status === "Pending") {
			frappe.throw(__("Approve or reject the discount first."));
		}
	},
});
