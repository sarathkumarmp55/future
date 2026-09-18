# Copyright (c) 2026, future and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters=None):
	filters = filters or {}
	as_on_date = getdate(filters.get("as_on_date") or frappe.utils.nowdate())

	columns = get_columns()
	data = get_data(as_on_date)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Lead Owner Name"),
			"fieldname": "lead_owner_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Lead Owner"),
			"fieldname": "lead_owner",
			"fieldtype": "Link",
			"options": "User",
			"width": 140,
		},
		{
			"label": _("Overdue"),
			"fieldname": "overdue",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Pending"),
			"fieldname": "pending",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Total Task Count"),
			"fieldname": "total_task_count",
			"fieldtype": "Int",
			"width": 140,
		},
	]


def get_data(as_on_date):
	rows = frappe.db.sql(
		"""
		SELECT
			`tabLead`.lead_owner,
			IFNULL(`tabUser`.full_name, `tabLead`.lead_owner) AS lead_owner_name,
			SUM(CASE WHEN `tabToDo`.status = 'Open' AND `tabToDo`.date < %(as_on_date)s THEN 1 ELSE 0 END) AS overdue,
			SUM(CASE WHEN `tabToDo`.status = 'Open' AND `tabToDo`.date >= %(as_on_date)s THEN 1 ELSE 0 END) AS pending
		FROM
			`tabToDo`
		LEFT JOIN `tabLead`
			ON `tabLead`.name = `tabToDo`.reference_name
			AND `tabToDo`.reference_type = 'Lead'
		LEFT JOIN `tabUser`
			ON `tabUser`.name = `tabLead`.lead_owner
		WHERE
			`tabToDo`.status = 'Open'
			AND `tabToDo`.reference_type = 'Lead'
		GROUP BY
			`tabLead`.lead_owner, `tabUser`.full_name
		ORDER BY
			`tabUser`.full_name, `tabLead`.lead_owner
		""",
		{"as_on_date": as_on_date},
		as_dict=1,
	)

	data = []
	for r in rows:
		overdue = int(r.overdue or 0)
		pending = int(r.pending or 0)
		data.append(
			{
				"lead_owner": r.lead_owner or "",
				"lead_owner_name": r.lead_owner_name or _("Not Assigned"),
				"overdue": overdue,
				"pending": pending,
				"total_task_count": overdue + pending,
			}
		)

	return data
