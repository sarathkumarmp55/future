// Lead form: "Hand Over" button and hand-over history, for people who manage leads.
frappe.ui.form.on("Lead", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(
			__("Hand-over History"),
			() => frappe.set_route("List", "Lead Handover", { lead: frm.doc.name }),
			__("Hand Over")
		);
		frappe.xcall("future.lead_management.get_handover_context").then((ctx) => {
			if (!ctx.can_manage) {
				add_request_button(frm);
				return;
			}
			frm.add_custom_button(
				__("Hand Over This Lead"),
				() => {
					const d = new frappe.ui.Dialog({
						title: __("Hand over {0}", [frm.doc.lead_name || frm.doc.name]),
						fields: [
							{ fieldname: "to_user", fieldtype: "Autocomplete", label: __("Hand over to"), options: ctx.users, reqd: 1 },
							{ fieldname: "role", fieldtype: "Select", label: __("As"), options: ["Lead User", "Team Lead", "Lead Manager"], default: "Lead User", reqd: 1 },
							{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
						],
						primary_action_label: __("Hand Over"),
						primary_action(v) {
							frappe
								.xcall("future.lead_management.quick_handover", {
									leads: [frm.doc.name],
									to_users: [v.to_user],
									role: v.role,
									reason: v.reason,
								})
								.then((r) => {
									d.hide();
									frappe.show_alert({ message: __("Handed over. Logged as {0}.", [r.name]), indicator: "green" });
									frm.reload_doc();
								});
						},
					});
					d.show();
				},
				__("Hand Over")
			);
		});
	},
});

function add_request_button(frm) {
	frappe.xcall("future.lead_management.get_request_context", { lead: frm.doc.name }).then((ctx) => {
		if (!ctx.can_request) return;
		frm.add_custom_button(
			__("Request Hand-over"),
			() => {
				const d = new frappe.ui.Dialog({
					title: __("Ask your Team Lead to move this lead"),
					fields: [
						{
							fieldname: "reason",
							fieldtype: "Small Text",
							label: __("Why?"),
							reqd: 1,
							description: __("For example: language barrier, parent prefers a male/female counsellor, location."),
						},
						{
							fieldname: "to_user",
							fieldtype: "Autocomplete",
							label: __("Suggest a colleague (optional)"),
							options: ctx.colleagues,
						},
					],
					primary_action_label: __("Send Request"),
					primary_action(v) {
						frappe
							.xcall("future.lead_management.request_handover", {
								leads: [frm.doc.name],
								reason: v.reason,
								to_user: v.to_user || null,
							})
							.then((name) => {
								d.hide();
								frappe.show_alert({ message: __("Request {0} sent to your Team Lead", [name]), indicator: "green" });
							});
					},
				});
				d.show();
			},
			__("Hand Over")
		);
	});
}
