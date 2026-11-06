frappe.ui.form.on("Lead Handover", {
	setup(frm) {
		frm.set_indicator_formatter("lead", (row) => (row.to_user ? "blue" : "gray"));
	},

	onload(frm) {
		frappe.xcall("future.lead_management.get_handover_context").then((ctx) => {
			frm._handover_ctx = ctx;
			const names = ctx.users.map((u) => u.value);
			const team_query = () => ({ filters: { name: ["in", names], enabled: 1 } });
			frm.set_query("to_user", team_query);
			frm.set_query("from_user", team_query);
			frm.set_query("user", "targets", team_query);
			frm.set_query("to_user", "leads", team_query);
			if (!ctx.can_manage && frm.is_new()) {
				frm.set_intro(
					__("Only Team Leads, Lead Managers and Sales Managers can hand over leads."),
					"orange"
				);
			}
		});
	},

	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.request_status === "Requested" && !frm.is_new()) {
			frm.set_intro(
				__("{0} asks to hand over these leads. Reason: {1}", [
					frappe.user.full_name(frm.doc.requested_by),
					frappe.utils.escape_html(frm.doc.reason || ""),
				]),
				"orange"
			);
			frappe.xcall("future.lead_management.get_handover_context").then((ctx) => {
				if (!ctx.can_manage) return;
				frm.page.set_primary_action(__("Approve & Hand Over"), () => {
					if (!frm.doc.to_user) {
						frappe.msgprint(__("Choose who the leads go to, save, then approve."));
						return;
					}
					frm.save("Submit");
				});
				frm.add_custom_button(__("Reject"), () => {
					frappe.prompt(
						{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
						(v) =>
							frappe
								.xcall("future.lead_management.reject_request", { name: frm.doc.name, reason: v.reason })
								.then(() => frm.reload_doc()),
						__("Reject request"),
						__("Reject")
					);
				});
			});
		}
		if (frm.doc.docstatus === 0 && frm.doc.request_status === "Rejected") {
			frm.set_intro(__("This request was rejected. See the comments for the reason."), "red");
		}
		if (frm.doc.docstatus === 1) {
			frm.set_intro(
				__("{0} leads handed over by {1} on {2}.", [
					frm.doc.total_leads,
					frappe.user.full_name(frm.doc.handed_over_by),
					frappe.datetime.str_to_user(frm.doc.handover_on),
				]),
				"green"
			);
		}
	},

	get_leads(frm) {
		if (!frm.doc.from_user) {
			frappe.msgprint(__("Choose who to take leads from first."));
			return;
		}
		const statuses = (frm.doc.pick_statuses || "")
			.split("\n")
			.map((s) => s.trim())
			.filter(Boolean);
		frappe
			.xcall("future.lead_management.get_leads_held_by", {
				user: frm.doc.from_user,
				role: frm.doc.role,
				statuses,
				limit: frm.doc.pick_count || 0,
				oldest_first: frm.doc.oldest_first,
			})
			.then((rows) => {
				const existing = new Set((frm.doc.leads || []).map((r) => r.lead));
				let added = 0;
				rows.forEach((r) => {
					if (existing.has(r.name)) return;
					frm.add_child("leads", {
						lead: r.name,
						lead_name: r.lead_name,
						lead_status: r.status,
						from_users: frm.doc.from_user,
					});
					added++;
				});
				frm.refresh_field("leads");
				frm.set_value("total_leads", (frm.doc.leads || []).length);
				frappe.show_alert({
					message: __("Added {0} of {1}'s leads", [added, frappe.user.full_name(frm.doc.from_user)]),
					indicator: added ? "green" : "orange",
				});
			});
	},
});
