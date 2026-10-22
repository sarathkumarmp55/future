# Copyright (c) 2026, future and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

LEAD_ROLE = "Lead Manager"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	user = filters.get("user") or frappe.session.user

	data = get_data(user, getdate(nowdate()))
	return [], [], None, None, get_report_summary(data)


def get_data(user, today):
	row = frappe.db.sql(
		"""
		SELECT
			SUM(CASE WHEN `tabToDo`.status = 'Open' AND `tabToDo`.date < %(today)s THEN 1 ELSE 0 END) AS overdue,
			SUM(CASE WHEN `tabToDo`.status = 'Open' THEN 1 ELSE 0 END) AS open,
			SUM(CASE WHEN `tabToDo`.status = 'Closed' THEN 1 ELSE 0 END) AS closed
		FROM
			`tabToDo`
		WHERE
			`tabToDo`.allocated_to = %(user)s
			AND `tabToDo`.custom_lead_role = %(lead_role)s
		""",
		{"user": user, "lead_role": LEAD_ROLE, "today": today},
		as_dict=1,
	)

	row = row[0] if row else {}

	return {
		"overdue": int(row.get("overdue") or 0),
		"open": int(row.get("open") or 0),
		"closed": int(row.get("closed") or 0),
	}


def get_report_summary(data):
	return [
		{
			"label": _("Overdue"),
			"value": data["overdue"],
			"datatype": "Int",
			"indicator": "Red",
		},
		{
			"label": _("Open"),
			"value": data["open"],
			"datatype": "Int",
			"indicator": "Orange",
		},
		{
			"label": _("Closed"),
			"value": data["closed"],
			"datatype": "Int",
			"indicator": "Green",
		},
	]
