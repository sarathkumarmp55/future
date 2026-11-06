"""Beds per hostel and room type: capacity, occupied, free, occupancy %, and dues."""

import frappe
from frappe import _
from frappe.utils import cint, flt

from future.hostel_management import occupancy


def execute(filters=None):
	filters = frappe._dict(filters or {})
	hf = {"status": filters.status} if filters.get("status") else {}
	if filters.get("location"):
		hf["location"] = filters.location
	hostels = frappe.get_all(
		"Hostel",
		filters=hf,
		fields=["name", "hostel_name", "hostel_code", "location", "status", "ac_capacity", "non_ac_capacity", "monthly_rent"],
		order_by="location, hostel_name",
	)
	dues = dict(
		frappe.db.sql(
			"""select custom_hostel, sum(custom_hostel_balance) from `tabProgram Enrollment`
			where docstatus = 1 and custom_hosteller = 'Hosteller' and custom_hostel_status = 'Allotted'
			group by custom_hostel"""
		)
	)
	rows = []
	for h in hostels:
		occ = occupancy(h.name)
		cap = cint(h.ac_capacity) + cint(h.non_ac_capacity)
		used = occ["AC"] + occ["Non AC"]
		rows.append(
			{
				"hostel": h.name,
				"hostel_name": h.hostel_name or h.name,
				"code": h.hostel_code,
				"location": h.location,
				"status": h.status,
				"ac_capacity": cint(h.ac_capacity),
				"ac_occupied": occ["AC"],
				"non_ac_capacity": cint(h.non_ac_capacity),
				"non_ac_occupied": occ["Non AC"],
				"capacity": cap,
				"occupied": used,
				"free": max(cap - used, 0),
				"occupancy": round(used * 100.0 / cap, 1) if cap else 0,
				"dues": flt(dues.get(h.name)),
				"monthly_rent": flt(h.monthly_rent),
			}
		)
	columns = [
		{"fieldname": "hostel", "label": _("Hostel"), "fieldtype": "Link", "options": "Hostel", "width": 120},
		{"fieldname": "hostel_name", "label": _("Name"), "fieldtype": "Data", "width": 140},
		{"fieldname": "location", "label": _("Location"), "fieldtype": "Data", "width": 110},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 90},
		{"fieldname": "ac_occupied", "label": _("AC Used"), "fieldtype": "Int", "width": 80},
		{"fieldname": "ac_capacity", "label": _("AC Beds"), "fieldtype": "Int", "width": 80},
		{"fieldname": "non_ac_occupied", "label": _("Non AC Used"), "fieldtype": "Int", "width": 100},
		{"fieldname": "non_ac_capacity", "label": _("Non AC Beds"), "fieldtype": "Int", "width": 100},
		{"fieldname": "free", "label": _("Free Beds"), "fieldtype": "Int", "width": 90},
		{"fieldname": "occupancy", "label": _("Occupancy %"), "fieldtype": "Percent", "width": 110},
		{"fieldname": "dues", "label": _("Hostel Fee Balance"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "monthly_rent", "label": _("Monthly Rent"), "fieldtype": "Currency", "width": 120},
	]
	cap = sum(r["capacity"] for r in rows)
	used = sum(r["occupied"] for r in rows)
	summary = [
		{"label": _("Hostels"), "value": len(rows), "datatype": "Int"},
		{"label": _("Beds"), "value": cap, "datatype": "Int"},
		{"label": _("Occupied"), "value": used, "datatype": "Int", "indicator": "Blue"},
		{"label": _("Free"), "value": cap - used, "datatype": "Int", "indicator": "Green"},
		{"label": _("Occupancy"), "value": f"{round(used * 100.0 / cap, 1) if cap else 0}%", "datatype": "Data"},
		{"label": _("Hostel Fee Balance"), "value": sum(r["dues"] for r in rows), "datatype": "Currency", "indicator": "Red"},
	]
	chart = {
		"data": {
			"labels": [r["hostel_name"] for r in rows if r["capacity"]],
			"datasets": [
				{"name": _("Occupied"), "values": [r["occupied"] for r in rows if r["capacity"]]},
				{"name": _("Free"), "values": [r["free"] for r in rows if r["capacity"]]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"colors": ["#2a78d6", "#cbd5e1"],
	}
	return columns, rows, None, chart, summary
