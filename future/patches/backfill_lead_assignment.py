import frappe


def execute():
	"""Set Lead.custom_lead_user / custom_assigned_on from existing open assignments, so the
	first-call SLA and the "Past First-call Limit" tile work on leads assigned before v16."""
	if not frappe.db.has_column("Lead", "custom_assigned_on"):
		return
	frappe.db.sql(
		"""update `tabLead` l
		inner join (
			select t.reference_name as lead, min(t.creation) as assigned_on,
				substring_index(group_concat(t.allocated_to order by t.creation desc), ',', 1) as holder
			from `tabToDo` t
			where t.reference_type = 'Lead' and t.status = 'Open'
			and (ifnull(t.custom_lead_role, '') = '' or t.custom_lead_role = 'Lead User')
			and t.allocated_to not in (select user from `tabTeam Heirarchy`)
			group by t.reference_name
		) a on a.lead = l.name
		set l.custom_assigned_on = ifnull(l.custom_assigned_on, a.assigned_on),
			l.custom_lead_user = ifnull(nullif(l.custom_lead_user, ''), a.holder),
			l.custom_sla_alerted_on = ifnull(l.custom_sla_alerted_on, now())"""
	)
