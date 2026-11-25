frappe.query_reports["Lead Conversion by Uploader"] = {
	filters: [
		{ fieldname: "from_date", label: __("Uploaded From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Uploaded To"), fieldtype: "Date" },
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["Uploaded By", "Lead Source", "Salesperson"],
			default: "Uploaded By",
		},
		{ fieldname: "uploaded_by", label: __("Uploaded By"), fieldtype: "Link", options: "User" },
	],
};
