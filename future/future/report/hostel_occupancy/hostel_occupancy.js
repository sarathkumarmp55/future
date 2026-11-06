frappe.query_reports["Hostel Occupancy"] = {
	filters: [
		{ fieldname: "location", label: __("Location"), fieldtype: "Link", options: "Location" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: ["", "Active", "Yet to Open", "Vacated"], default: "Active" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "occupancy" && data) {
			const color = data.occupancy >= 95 ? "red" : data.occupancy >= 75 ? "orange" : "green";
			value = `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
