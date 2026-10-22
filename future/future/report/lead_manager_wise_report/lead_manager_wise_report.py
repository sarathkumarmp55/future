# Copyright (c) 2026, future and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from future.api import get_team_lead_users, is_lead_manager


def execute(filters=None):
	filters = frappe._dict(filters or {})
	lead_manager = filters.get("lead_manager") or frappe.session.user
	today = getdate(filters.get("today") or nowdate())
	from_date = getdate(filters.get("from_date") or today)
	to_date = getdate(filters.get("to_date") or today)

	if not is_lead_manager(lead_manager):
		frappe.throw(_("{0} is not a Lead Manager in Team Heirarchy").format(lead_manager))

	lead_users = _get_lead_users(lead_manager, filters.get("lead_users"))
	counts = _get_counts([user.value for user in lead_users], from_date, to_date, today)

	data = []
	summary = {"overdue": 0, "open": 0, "closed": 0}

	for user in lead_users:
		row = counts.get(user.value) or {}
		data.append(
			{
				"lead_user": user.value,
				"lead_user_name": user.label,
				"overdue": row.get("overdue", 0),
				"open": row.get("open", 0),
				"closed": row.get("closed", 0),
			}
		)
		summary["overdue"] += row.get("overdue", 0)
		summary["open"] += row.get("open", 0)
		summary["closed"] += row.get("closed", 0)

	return get_columns(), data, None, None, get_report_summary(summary)


def _get_lead_users(lead_manager, lead_users):
	users = [
		frappe._dict(user)
		for user in get_team_lead_users(lead_manager, role="Lead Manager")
	]

	if isinstance(lead_users, str):
		lead_users = frappe.parse_json(lead_users)

	if lead_users:
		users = [user for user in users if user.value in lead_users]

	return users


def _get_counts(users, from_date, to_date, today):
	if not users:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT
			`tabToDo`.allocated_to,
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
			`tabToDo`.allocated_to IN %(users)s
		GROUP BY
			`tabToDo`.allocated_to
		""",
		{
			"users": tuple(users),
			"today": today,
			"from_date": from_date,
			"to_date": to_date,
		},
		as_dict=1,
	)

	counts = {}
	for row in rows:
		counts[row.allocated_to] = {
			"overdue": int(row.overdue or 0),
			"open": int(row.open or 0),
			"closed": int(row.closed or 0),
		}

	return counts


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


def get_report_summary(summary):
	return [
		{
			"label": _("Overdue"),
			"value": summary["overdue"],
			"datatype": "Int",
			"indicator": "Red",
		},
		{
			"label": _("Open"),
			"value": summary["open"],
			"datatype": "Int",
			"indicator": "Orange",
		},
		{
			"label": _("Closed"),
			"value": summary["closed"],
			"datatype": "Int",
			"indicator": "Green",
		},
	]
