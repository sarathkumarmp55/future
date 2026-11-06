// Discount approvals, refund and transfer requests: tile strips (see list_tiles.js).
["Discount Approval Log", "Fee Refund Request", "Fee Transfer Request"].forEach((doctype) => {
	frappe.listview_settings[doctype] = Object.assign(frappe.listview_settings[doctype] || {}, {
		onload(listview) {
			listview.future_tiles = new FutureListTiles(listview, doctype);
		},
		refresh(listview) {
			listview.future_tiles && listview.future_tiles.schedule();
		},
	});
});
