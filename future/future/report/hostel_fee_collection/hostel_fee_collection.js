frappe.query_reports["Hostel Fee Collection"] = {
	filters: [
		{ fieldname: "month", label: __("Month"), fieldtype: "Date", default: frappe.datetime.month_start(), reqd: 1 },
		{ fieldname: "hostel", label: __("Hostel"), fieldtype: "Link", options: "Hostel" },
		{ fieldname: "room_type", label: __("Room"), fieldtype: "Select", options: ["", "AC", "Non AC"] },
		{ fieldname: "program", label: __("Program"), fieldtype: "Link", options: "Program" },
		{ fieldname: "status", label: __("Show"), fieldtype: "Select", options: ["Allotted", "All hostellers", "Due this month"], default: "Allotted" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "month_status" && data) {
			const color = data.month_status === "Paid" ? "green" : data.month_status === "Due" ? "red" : "gray";
			value = `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
};
