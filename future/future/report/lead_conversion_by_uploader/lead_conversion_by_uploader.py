"""How far the leads each person uploaded have got: status buckets and conversion rates.

Uploaders (Lead Settings > Lead uploader role) see only the leads they uploaded; people with
full access see all; everyone else sees the leads the hierarchy lets them see."""

import frappe
from frappe import _
from frappe.utils import flt

from future.permissions.visibility import is_unrestricted, is_uploader, lead_condition

BUCKETS = {
	"in_progress": (
		"Lead", "New", "Contacted", "Interested", "Demo Scheduled", "Negotiation", "Follow-up", "Qualified",
		"Set Reminder", "Schedule Callback", "Did Not Pick", "Reassign", "Manager Approval",
	),
	"opportunity": (
		"Opportunity", "Discount Approval Pending", "Discount Approved", "Payment Approval Pending", "Payment Done",
	),
	"converted": ("Converted Student", "Won"),
	"lost": ("Disqualified", "Invalid", "Lost", "Close Lead"),
}
GROUP_FIELDS = {"Uploaded By": "l.owner", "Lead Source": "l.utm_source", "Salesperson": "l.custom_lead_user"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	group = GROUP_FIELDS.get(filters.group_by or "Uploaded By", "l.owner")
	conditions, values = ["1 = 1"], {}
	user = frappe.session.user
	if not is_unrestricted(user):
		if is_uploader(user):
			conditions.append("l.owner = %(user)s")
			values["user"] = user
		else:
			conditions.append(lead_condition("l", user) or "1 = 1")
	if filters.from_date:
		conditions.append("date(l.creation) >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.to_date:
		conditions.append("date(l.creation) <= %(to_date)s")
		values["to_date"] = filters.to_date
	if filters.uploaded_by:
		conditions.append("l.owner = %(uploaded_by)s")
		values["uploaded_by"] = filters.uploaded_by

	sums = ", ".join(
		f"sum(l.status in ({', '.join(frappe.db.escape(s) for s in statuses)})) as {key}" for key, statuses in BUCKETS.items()
	)
	rows = frappe.db.sql(
		f"""select ifnull({group}, '') as grp, count(*) as leads,
			sum(ifnull(l.custom_lead_user, '') != '') as assigned, {sums}
		from `tabLead` l where {' and '.join(conditions)}
		group by grp order by leads desc""",
		values,
		as_dict=True,
	)
	names = dict(frappe.get_all("User", fields=["name", "full_name"], as_list=True)) if group != "l.utm_source" else {}
	data = []
	for r in rows:
		leads = flt(r.leads)
		other = leads - sum(flt(r[k]) for k in BUCKETS)
		data.append(
			{
				"grp": r.grp or _("(not set)"),
				"grp_name": names.get(r.grp) or "",
				"leads": r.leads,
				"assigned": r.assigned,
				"not_assigned": leads - flt(r.assigned),
				"in_progress": flt(r.in_progress) + other,
				"opportunity": r.opportunity,
				"converted": r.converted,
				"lost": r.lost,
				"opportunity_rate": round((flt(r.opportunity) + flt(r.converted)) * 100 / leads, 1) if leads else 0,
				"conversion_rate": round(flt(r.converted) * 100 / leads, 1) if leads else 0,
			}
		)
	return columns(filters), data, None, chart(data)


def columns(filters):
	label = filters.group_by or "Uploaded By"
	link = {"Lead Source": ("Link", "UTM Source")}.get(label, ("Link", "User"))
	return [
		{"label": _(label), "fieldname": "grp", "fieldtype": link[0], "options": link[1], "width": 220},
		{"label": _("Name"), "fieldname": "grp_name", "fieldtype": "Data", "width": 160},
		{"label": _("Leads"), "fieldname": "leads", "fieldtype": "Int", "width": 80},
		{"label": _("Assigned"), "fieldname": "assigned", "fieldtype": "Int", "width": 90},
		{"label": _("Not Assigned"), "fieldname": "not_assigned", "fieldtype": "Int", "width": 100},
		{"label": _("In Progress"), "fieldname": "in_progress", "fieldtype": "Int", "width": 100},
		{"label": _("Opportunity"), "fieldname": "opportunity", "fieldtype": "Int", "width": 100},
		{"label": _("Converted"), "fieldname": "converted", "fieldtype": "Int", "width": 95},
		{"label": _("Lost / Invalid"), "fieldname": "lost", "fieldtype": "Int", "width": 105},
		{"label": _("Opportunity %"), "fieldname": "opportunity_rate", "fieldtype": "Percent", "width": 110},
		{"label": _("Conversion %"), "fieldname": "conversion_rate", "fieldtype": "Percent", "width": 105},
	]


def chart(data):
	top = data[:10]
	if not top:
		return None
	return {
		"data": {
			"labels": [d["grp_name"] or d["grp"] for d in top],
			"datasets": [
				{"name": _("In Progress"), "values": [d["in_progress"] for d in top]},
				{"name": _("Opportunity"), "values": [d["opportunity"] for d in top]},
				{"name": _("Converted"), "values": [d["converted"] for d in top]},
				{"name": _("Lost / Invalid"), "values": [d["lost"] for d in top]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}
