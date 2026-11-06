// Program Enrollment list: admissions tiles (see list_tiles.js / future.list_tiles).
frappe.listview_settings["Program Enrollment"] = Object.assign(frappe.listview_settings["Program Enrollment"] || {}, {
	add_fields: ["custom_admission_status", "custom_course_balance"],
	get_indicator(doc) {
		if (doc.docstatus === 2) return [__("Cancelled"), "red", "docstatus,=,2"];
		const s = doc.custom_admission_status || "Pending";
		const color = { Pending: "orange", Joined: "green", Completed: "blue", Dropped: "gray", Cancelled: "red" }[s] || "gray";
		return [__(s), color, `custom_admission_status,=,${s}`];
	},
	onload(listview) {
		listview.future_tiles = new FutureListTiles(listview, "Program Enrollment");
	},
	refresh(listview) {
		listview.future_tiles && listview.future_tiles.schedule();
	},
});
