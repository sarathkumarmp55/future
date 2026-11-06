// Follow-ups (ToDo) and Lead Hand-overs: clickable tile strips (see list_tiles.js).
["ToDo", "Lead Handover"].forEach((doctype) => {
	frappe.listview_settings[doctype] = Object.assign(frappe.listview_settings[doctype] || {}, {
		onload(listview) {
			listview.future_tiles = new FutureListTiles(listview, doctype);
		},
		refresh(listview) {
			listview.future_tiles && listview.future_tiles.schedule();
		},
	});
});
