// Lead Handover rows: one status label that reads like the process.
frappe.listview_settings["Lead Handover"] = Object.assign(frappe.listview_settings["Lead Handover"] || {}, {
	add_fields: ["request_status", "handover_type"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		if (doc.docstatus === 2) return [__("Cancelled"), "gray", "docstatus,=,2"];
		if (doc.docstatus === 1) return [__("Handed Over"), "green", "docstatus,=,1"];
		if (doc.request_status === "Rejected") return [__("Rejected"), "red", "request_status,=,Rejected"];
		if (doc.request_status === "Requested") return [__("Request Waiting"), "orange", "request_status,=,Requested"];
		return [__("Draft"), "gray", "docstatus,=,0"];
	},
});
