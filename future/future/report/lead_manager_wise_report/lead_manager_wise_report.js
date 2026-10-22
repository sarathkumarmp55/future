frappe.query_reports["Lead Manager Wise Report"] = {
	filters: [
		{
			fieldname: "lead_manager",
			label: __("Lead Manager"),
			fieldtype: "Link",
			options: "User",
			default: frappe.session.user,
			read_only: 1,
			reqd: 1,
			on_change: () => {
				clear_lead_users();
				validate_lead_manager(frappe.query_report.get_filter_value("lead_manager")).then(
					(is_lead_manager) => {
						if (is_lead_manager) {
							frappe.query_report.refresh();
						}
					}
				);
			},
		},
		{
			fieldname: "lead_users",
			label: __("Lead User"),
			fieldtype: "MultiSelectList",
			get_data: (txt) => {
				const lead_manager = frappe.query_report.get_filter_value("lead_manager");
				if (!lead_manager) {
					return [];
				}
				return frappe
					.xcall("future.api.get_team_lead_users", {
						team_lead: lead_manager,
						role: "Lead Manager",
					})
					.then((users) =>
						users.filter(
							(user) =>
								!txt ||
								(user.label || "").toLowerCase().includes(txt.toLowerCase()) ||
								(user.value || "").toLowerCase().includes(txt.toLowerCase())
						)
					);
			},
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.nowdate(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.nowdate(),
			reqd: 1,
		},
		{
			fieldname: "today",
			label: __("Today"),
			fieldtype: "Date",
			default: frappe.datetime.nowdate(),
			read_only: 1,
		},
	],

	onload: (report) => {
		validate_lead_manager(report.get_filter_value("lead_manager"));
	},
};

function clear_lead_users() {
	const lead_users = frappe.query_report && frappe.query_report.get_filter("lead_users");
	if (lead_users && lead_users.clear_all_selections) {
		lead_users.clear_all_selections();
	}
}

function validate_lead_manager(user) {
	if (!user) {
		return Promise.resolve(false);
	}
	return frappe.xcall("future.api.is_lead_manager", { user: user }).then((is_lead_manager) => {
		if (!is_lead_manager) {
			frappe.msgprint({
				title: __("Invalid User"),
				message: __("{0} is not a Lead Manager in Team Heirarchy", [user]),
				indicator: "red",
			});
		}
		return is_lead_manager;
	});
}
