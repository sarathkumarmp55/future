// Opportunity list: clickable tile strip (see list_tiles.js / future.list_tiles).
frappe.listview_settings["Opportunity"] = Object.assign(frappe.listview_settings["Opportunity"] || {}, {
	onload(listview) {
		listview.future_tiles = new FutureListTiles(listview, "Opportunity");
	},
	refresh(listview) {
		listview.future_tiles && listview.future_tiles.schedule();
	},
});
