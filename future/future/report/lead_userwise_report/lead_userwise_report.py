# Copyright (c) 2026, future and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	user = filters.get("user") or frappe.session.user
	today = getdate(nowdate())
	from_date = getdate(filters.get("from_date") or today)
	to_date = getdate(filters.get("to_date") or today)

	data = get_data(user, from_date, to_date, today)
	return get_columns(), [data], None, None, get_report_summary(data)


def get_data(user, from_date, to_date, today):
	row = frappe.db.sql(
		"""
		SELECT
			SUM(CASE WHEN `tabToDo`.status = 'Open' AND `tabToDo`.date < %(today)s THEN 1 ELSE 0 END) AS overdue,
			SUM(
				CASE
					WHEN `tabToDo`.status = 'Open'
						AND `tabToDo`.date >= %(from_date)s
						AND `tabToDo`.date <= %(to_date)s
					THEN 1
					ELSE 0
				END
			) AS open,
			SUM(
				CASE
					WHEN `tabToDo`.status = 'Closed'
						AND `tabToDo`.date >= %(from_date)s
						AND `tabToDo`.date <= %(to_date)s
					THEN 1
					ELSE 0
				END
			) AS closed
		FROM
			`tabToDo`
		WHERE
			`tabToDo`.allocated_to = %(user)s
		""",
		{
			"user": user,
			"today": today,
			"from_date": from_date,
			"to_date": to_date,
		},
		as_dict=1,
	)

	row = row[0] if row else {}

	return {
		"lead_user": user,
		"lead_user_name": frappe.db.get_value("User", user, "full_name") or user,
		"overdue": int(row.get("overdue") or 0),
		"open": int(row.get("open") or 0),
		"closed": int(row.get("closed") or 0),
	}


def get_columns():
	return [
		{
			"label": _("Lead User"),
			"fieldname": "lead_user",
			"fieldtype": "Link",
			"options": "User",
			"width": 200,
		},
		{
			"label": _("Lead User Name"),
			"fieldname": "lead_user_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Overdue"),
			"fieldname": "overdue",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Open"),
			"fieldname": "open",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Closed"),
			"fieldname": "closed",
			"fieldtype": "Int",
			"width": 100,
		},
	]


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
