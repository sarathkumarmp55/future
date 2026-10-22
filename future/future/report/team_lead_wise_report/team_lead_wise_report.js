frappe.query_reports["Team Lead Wise Report"] = {
	filters: [
		{
			fieldname: "team_lead",
			label: __("User ID"),
			fieldtype: "Link",
			options: "User",
			default: frappe.session.user,
			read_only: 1,
			reqd: 1,
			on_change: () => {
				clear_lead_users();
				validate_team_lead(frappe.query_report.get_filter_value("team_lead")).then(
					(is_team_lead) => {
						if (is_team_lead) {
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
				const team_lead = frappe.query_report.get_filter_value("team_lead");
				if (!team_lead) {
					return [];
				}
				return frappe
					.xcall("future.api.get_team_lead_users", { team_lead: team_lead })
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
		allow_lead_manager_to_change_user(report).then((is_lead_manager) => {
			if (!is_lead_manager) {
				validate_team_lead(report.get_filter_value("team_lead"));
			}
		});
	},
};

function allow_lead_manager_to_change_user(report) {
	return frappe
		.xcall("future.api.is_lead_manager", { user: frappe.session.user })
		.then((is_lead_manager) => {
			if (is_lead_manager) {
				const team_lead = report.get_filter("team_lead");
				if (team_lead) {
					team_lead.df.read_only = 0;
					team_lead.refresh();
				}
			}
			return is_lead_manager;
		});
}

function clear_lead_users() {
	const lead_users = frappe.query_report && frappe.query_report.get_filter("lead_users");
	if (lead_users && lead_users.clear_all_selections) {
		lead_users.clear_all_selections();
	}
}

function validate_team_lead(user) {
	if (!user) {
		return Promise.resolve(false);
	}
	return frappe.xcall("future.api.is_team_lead", { user: user }).then((is_team_lead) => {
		if (!is_team_lead) {
			frappe.msgprint({
				title: __("Invalid User"),
				message: __("{0} is not a Team Lead in Team Heirarchy", [user]),
				indicator: "red",
			});
		}
		return is_team_lead;
	});
}
