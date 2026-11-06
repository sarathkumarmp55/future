"""Hostel fee collection sheet: one row per hosteller for the chosen month, with
what fell due that month, what is paid, the running balance and remarks."""

import frappe
from frappe import _
from frappe.utils import flt, get_first_day, get_last_day, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	month = getdate(filters.month or nowdate())
	start, end = get_first_day(month), get_last_day(month)

	cond, values = ["pe.docstatus = 1", "pe.custom_hosteller = 'Hosteller'"], {"start": start, "end": end}
	for key, col in (("hostel", "pe.custom_hostel"), ("room_type", "pe.custom_hostel_type"), ("program", "pe.program")):
		if filters.get(key):
			cond.append(f"{col} = %({key})s")
			values[key] = filters[key]
	if filters.get("status") == "Allotted":
		cond.append("pe.custom_hostel_status = 'Allotted'")

	rows = frappe.db.sql(
		f"""select pe.name as enrollment, pe.student, pe.student_name, pe.program, pe.custom_hostel as hostel,
			h.hostel_name, pe.custom_hostel_type as room_type, pe.custom_hostel_status as hostel_status,
			s.student_mobile_number as mobile, pe.custom_total_hostel_fee as total_fee,
			pe.custom_hostel_paid as paid, pe.custom_hostel_balance as balance, pe.custom_hostel_remarks as remarks,
			ifnull(sum(case when fs.due_date between %(start)s and %(end)s then fs.final_amount end), 0) as month_due,
			ifnull(sum(case when fs.due_date between %(start)s and %(end)s then fs.paid_amount end), 0) as month_paid,
			ifnull(sum(case when fs.due_date <= %(end)s then fs.final_amount - fs.paid_amount end), 0) as due_till_month
		from `tabProgram Enrollment` pe
		left join `tabHostel` h on h.name = pe.custom_hostel
		left join `tabStudent` s on s.name = pe.student
		left join `tabEnrollment Fee Schedule` fs on fs.parent = pe.name and fs.parentfield = 'custom_hostel_schedule'
		where {' and '.join(cond)}
		group by pe.name
		order by h.hostel_name, pe.student_name""",
		values,
		as_dict=True,
	)
	for r in rows:
		r.month_balance = flt(r.month_due) - flt(r.month_paid)
		r.month_status = "Paid" if r.month_due and r.month_balance <= 0 else "Due" if r.month_due else "-"
	if filters.get("status") == "Due this month":
		rows = [r for r in rows if r.month_balance > 0]

	columns = [
		{"fieldname": "student_name", "label": _("Student"), "fieldtype": "Data", "width": 190},
		{"fieldname": "mobile", "label": _("Mobile"), "fieldtype": "Data", "width": 110},
		{"fieldname": "hostel_name", "label": _("Hostel"), "fieldtype": "Data", "width": 130},
		{"fieldname": "room_type", "label": _("Room"), "fieldtype": "Data", "width": 70},
		{"fieldname": "hostel_status", "label": _("Status"), "fieldtype": "Data", "width": 80},
		{"fieldname": "month_due", "label": _("Due This Month"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "month_paid", "label": _("Paid This Month"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "month_status", "label": _("Month"), "fieldtype": "Data", "width": 70},
		{"fieldname": "due_till_month", "label": _("Unpaid Till Month End"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "total_fee", "label": _("Total Hostel Fee"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "paid", "label": _("Total Paid"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "balance", "label": _("Balance"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "remarks", "label": _("Remarks"), "fieldtype": "Data", "width": 200},
		{"fieldname": "enrollment", "label": _("Enrollment"), "fieldtype": "Link", "options": "Program Enrollment", "width": 150},
	]
	due = sum(flt(r.month_due) for r in rows)
	paid = sum(flt(r.month_paid) for r in rows)
	summary = [
		{"label": _("Hostellers"), "value": len(rows), "datatype": "Int"},
		{"label": _("Due This Month"), "value": due, "datatype": "Currency"},
		{"label": _("Collected This Month"), "value": paid, "datatype": "Currency", "indicator": "Green"},
		{"label": _("Pending This Month"), "value": due - paid, "datatype": "Currency", "indicator": "Red" if due - paid > 0 else "Green"},
		{"label": _("Unpaid Till Month End"), "value": sum(flt(r.due_till_month) for r in rows), "datatype": "Currency", "indicator": "Orange"},
	]
	return columns, rows, None, None, summary
