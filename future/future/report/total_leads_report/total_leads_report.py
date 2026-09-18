# Copyright (c) 2026, future and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days


def execute(filters=None):
	filters = filters or {}
	from_date, to_date = get_date_range(filters)
	date_series = get_date_series(from_date, to_date)

	columns = get_columns(date_series)
	data = get_data(filters, date_series)
	return columns, data


def get_date_range(filters):
	if filters.get("from_date") and filters.get("to_date"):
		return getdate(filters["from_date"]), getdate(filters["to_date"])

	today = getdate()
	return add_days(today, -14), today


def get_date_series(from_date, to_date):
	dates = []
	current = from_date
	while current <= to_date:
		dates.append(current)
		current = add_days(current, 1)
	return dates


def get_columns(date_series):
	columns = [
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
			"label": _("Lead Count"),
			"fieldname": "lead_count",
			"fieldtype": "Int",
			"width": 100,
		},
	]

	for idx, date in enumerate(date_series, start=1):
		columns.append(
			{
				"label": _("Day {0}\n({1})").format(idx, frappe.utils.formatdate(date)),
				"fieldname": "day_{0}".format(idx),
				"fieldtype": "Int",
				"width": 90,
			}
		)

	columns.append(
		{
			"label": _("Total Lead Count"),
			"fieldname": "total_lead_count",
			"fieldtype": "Int",
			"width": 130,
		}
	)
	return columns


def get_data(filters, date_series):
	from_date, to_date = get_date_range(filters)

	conditions = ""
	params = {"from_date": from_date, "to_date": to_date}

	if filters.get("status"):
		conditions += " AND `tabLead`.status = %(status)s"
		params["status"] = filters["status"]

	rows = frappe.db.sql(
		f"""
		SELECT
			`tabLead`.lead_owner,
			IFNULL(`tabUser`.full_name, `tabLead`.lead_owner) AS lead_owner_name,
			DATE(`tabLead`.creation) AS lead_date,
			COUNT(*) AS count
		FROM
			`tabLead`
		LEFT JOIN `tabUser`
			ON `tabUser`.name = `tabLead`.lead_owner
		WHERE
			DATE(`tabLead`.creation) BETWEEN %(from_date)s AND %(to_date)s
			{conditions}
		GROUP BY
			`tabLead`.lead_owner, `tabUser`.full_name, DATE(`tabLead`.creation)
		ORDER BY
			`tabUser`.full_name, `tabLead`.lead_owner
		""",
		params,
		as_dict=1,
	)

	owner_map = {}
	for r in rows:
		owner = r.lead_owner or ""
		name = r.lead_owner_name or _("Not Assigned")
		owner_map.setdefault(owner, {"lead_owner": owner, "lead_owner_name": name, "counts": {}})
		owner_map[owner]["counts"][getdate(r.lead_date)] = r.count

	data = []
	for owner, info in sorted(owner_map.items(), key=lambda x: x[1]["lead_owner_name"]):
		row = {
			"lead_owner": info["lead_owner"],
			"lead_owner_name": info["lead_owner_name"],
		}
		total = 0
		for idx, date in enumerate(date_series, start=1):
			count = info["counts"].get(date, 0)
			row["day_{0}".format(idx)] = count
			total += count
		row["lead_count"] = total
		row["total_lead_count"] = total
		data.append(row)

	return data
