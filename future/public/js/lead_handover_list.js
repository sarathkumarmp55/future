// Lead list: "Hand Over" and "Distribute" bulk actions for Team Leads, Lead
// Managers and Sales Managers. Both create a submitted Lead Handover, so every
// move is logged. Loaded after lead_list.js (see hooks.doctype_list_js).

(function () {
	const settings = (frappe.listview_settings["Lead"] = frappe.listview_settings["Lead"] || {});
	const previous_onload = settings.onload;

	settings.onload = function (listview) {
		previous_onload && previous_onload.apply(this, arguments);
		frappe.xcall("future.lead_management.get_handover_context").then((ctx) => {
			if (!ctx.can_manage) return;
			listview.page.add_actions_menu_item(__("Hand Over"), () => open_dialog(listview, ctx, false), false);
			listview.page.add_actions_menu_item(__("Distribute"), () => open_dialog(listview, ctx, true), false);
		});
	};

	function open_dialog(listview, ctx, distribute) {
		const leads = listview.get_checked_items(true);
		if (!leads.length) {
			frappe.msgprint(__("Select the leads to move first."));
			return;
		}
		const d = new frappe.ui.Dialog({
			title: distribute
				? __("Distribute {0} leads", [leads.length])
				: __("Hand over {0} leads", [leads.length]),
			fields: [
				distribute
					? {
							fieldname: "to_users",
							fieldtype: "MultiSelectList",
							label: __("Split evenly between"),
							reqd: 1,
							get_data: (txt) =>
								ctx.users.filter(
									(u) => !txt || u.label.toLowerCase().includes(txt.toLowerCase())
								),
					  }
					: {
							fieldname: "to_user",
							fieldtype: "Autocomplete",
							label: __("Hand over to"),
							reqd: 1,
							options: ctx.users,
					  },
				{
					fieldname: "role",
					fieldtype: "Select",
					label: __("As"),
					options: ["Lead User", "Team Lead", "Lead Manager"],
					default: "Lead User",
					reqd: 1,
					description: __("Whoever held this position on the lead loses it."),
				},
				{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
			],
			primary_action_label: distribute ? __("Distribute") : __("Hand Over"),
			primary_action(values) {
				const to_users = distribute ? values.to_users : [values.to_user];
				if (distribute && (!to_users || to_users.length < 2)) {
					frappe.msgprint(__("Pick at least two people to distribute between."));
					return;
				}
				d.disable_primary_action();
				frappe
					.xcall("future.lead_management.quick_handover", {
						leads,
						to_users,
						role: values.role,
						reason: values.reason,
					})
					.then((r) => {
						d.hide();
						frappe.show_alert({
							message: __("{0} leads moved. Logged as {1}.", [
								r.count,
								`<a href="/desk/lead-handover/${r.name}">${r.name}</a>`,
							]),
							indicator: "green",
						});
						listview.clear_checked_items();
						listview.refresh();
					})
					.finally(() => d.enable_primary_action());
			},
		});
		d.show();
	}
})();
