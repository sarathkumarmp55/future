// Lead list: clickable tile strip (see list_tiles.js / future.list_tiles).
frappe.listview_settings["Lead"] = Object.assign(frappe.listview_settings["Lead"] || {}, {
	onload(listview) {
		listview.future_tiles = new FutureListTiles(listview, "Lead");
	},
	refresh(listview) {
		listview.future_tiles && listview.future_tiles.schedule();
	},
});
