// Payment Approval Log list: money totals + clickable tiles (see list_tiles.js /
// future.list_tiles). Replaces the old gradient dashboard and its separate date boxes:
// everything follows the list's own filters, and the theme handles light/dark.
frappe.listview_settings["Payment Approval Log"] = Object.assign(frappe.listview_settings["Payment Approval Log"] || {}, {
	add_fields: ["payment_status", "total_bill_amount"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		if (doc.docstatus === 2) return [__("Cancelled"), "gray", "docstatus,=,2"];
		if (doc.payment_status === "Rejected") return [__("Rejected"), "red", "payment_status,=,Rejected"];
		if (doc.docstatus === 1) return [__("Approved"), "green", "docstatus,=,1"];
		return [__("Pending"), "orange", "docstatus,=,0"];
	},
	onload(listview) {
		listview.future_tiles = new FutureListTiles(listview, "Payment Approval Log");
	},
	refresh(listview) {
		listview.future_tiles && listview.future_tiles.schedule();
	},
});
