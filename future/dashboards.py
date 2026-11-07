"""Data for the Hostel and Payments dashboards (desk pages hostel-dashboard and
payments-dashboard). Both are manager screens: the role check is repeated here because
the queries below read across all students."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, get_first_day, get_last_day, getdate, nowdate

MANAGER_ROLES = {"System Manager", "Sales Manager", "Accounts Manager", "Accounts User", "Academics User", "Education Manager"}


def _check():
	if not MANAGER_ROLES & set(frappe.get_roles()):
		frappe.throw(_("This dashboard is for managers and accounts."), frappe.PermissionError)


def _pct(part, whole):
	"""Whole percent, but one decimal under 10% so 1 of 362 reads 0.3% rather than 0%."""
	if not whole:
		return 0
	p = part * 100.0 / whole
	return round(p, 1) if 0 < p < 10 else round(p)


def _period(filters):
	to_date = getdate(filters.get("to_date") or nowdate())
	from_date = getdate(filters.get("from_date") or get_first_day(to_date))
	return (from_date, to_date) if from_date <= to_date else (to_date, from_date)


# ----------------------------------------------------------------------------- hostels


@frappe.whitelist()
def hostel_dashboard(filters=None):
	_check()
	from future.hostel_management import occupancy

	filters = frappe.parse_json(filters) if filters else {}
	month = getdate(filters.get("month") or nowdate())
	m_start, m_end = get_first_day(month), get_last_day(month)

	hf = {"status": "Active"}
	if filters.get("location"):
		hf["location"] = filters["location"]
	hostels = frappe.get_all(
		"Hostel",
		filters=hf,
		fields=["name", "hostel_name", "location", "ac_capacity", "non_ac_capacity"],
		order_by="location, hostel_name",
	)
	names = [h.name for h in hostels] or [""]

	dues = {
		r.hostel: r
		for r in frappe.db.sql(
			"""select pe.custom_hostel as hostel, sum(pe.custom_hostel_balance) as balance,
				sum(ifnull(o.overdue, 0)) as overdue
			from `tabProgram Enrollment` pe
			left join (
				select parent, sum(final_amount - paid_amount) as overdue from `tabEnrollment Fee Schedule`
				where parentfield = 'custom_hostel_schedule' and status = 'Overdue' group by parent
			) o on o.parent = pe.name
			where pe.docstatus = 1 and pe.custom_hostel_status = 'Allotted' and pe.custom_hostel in %(h)s
			group by pe.custom_hostel""",
			{"h": names},
			as_dict=True,
		)
	}
	rows = []
	for h in hostels:
		occ = occupancy(h.name)
		cap_ac, cap_non = cint(h.ac_capacity), cint(h.non_ac_capacity)
		used = occ["AC"] + occ["Non AC"]
		cap = cap_ac + cap_non
		d = dues.get(h.name) or {}
		rows.append(
			{
				"hostel": h.name,
				"name": h.hostel_name or h.name,
				"location": h.location,
				"ac": [occ["AC"], cap_ac],
				"non_ac": [occ["Non AC"], cap_non],
				"used": used,
				"capacity": cap,
				"free": max(cap - used, 0),
				"pct": _pct(used, cap),
				"balance": flt(d.get("balance")),
				"overdue": flt(d.get("overdue")),
			}
		)

	month_rows = frappe.db.sql(
		"""select sum(fs.final_amount) as due, sum(fs.paid_amount) as paid
		from `tabEnrollment Fee Schedule` fs
		inner join `tabProgram Enrollment` pe on pe.name = fs.parent and pe.docstatus = 1
		where fs.parentfield = 'custom_hostel_schedule' and fs.due_date between %(s)s and %(e)s
		and pe.custom_hostel in %(h)s""",
		{"s": m_start, "e": m_end, "h": names},
		as_dict=True,
	)[0]

	to_chase = frappe.db.sql(
		"""select pe.name as enrollment, pe.student_name, h.hostel_name, min(fs.due_date) as since,
			sum(fs.final_amount - fs.paid_amount) as overdue
		from `tabEnrollment Fee Schedule` fs
		inner join `tabProgram Enrollment` pe on pe.name = fs.parent and pe.docstatus = 1
		left join `tabHostel` h on h.name = pe.custom_hostel
		where fs.parentfield = 'custom_hostel_schedule' and fs.status = 'Overdue' and pe.custom_hostel in %(h)s
		group by pe.name order by overdue desc limit 8""",
		{"h": names},
		as_dict=True,
	)
	moves = frappe.db.sql(
		"""select pe.name as enrollment, pe.student_name, l.log_type, l.room_type, l.log_date, h.hostel_name, l.notes
		from `tabHostel Log` l
		inner join `tabProgram Enrollment` pe on pe.name = l.parent
		left join `tabHostel` h on h.name = l.hostel
		where l.parenttype = 'Program Enrollment' and l.hostel in %(h)s
		order by l.log_date desc, l.creation desc limit 8""",
		{"h": names},
		as_dict=True,
	)
	rows.sort(key=lambda r: (0 if r["capacity"] else 1))  # hostels without beds set go last
	cap = sum(r["capacity"] for r in rows)
	used = sum(r["used"] for r in rows)
	return {
		"month": str(m_start),
		"kpis": {
			"capacity": cap,
			"used": used,
			"free": max(cap - used, 0),
			"pct": _pct(used, cap),
			"month_due": flt(month_rows.due),
			"month_paid": flt(month_rows.paid),
			"balance": sum(r["balance"] for r in rows),
			"overdue": sum(r["overdue"] for r in rows),
		},
		"hostels": rows,
		"to_chase": to_chase,
		"moves": moves,
	}


# ----------------------------------------------------------------------------- payments


@frappe.whitelist()
def payments_dashboard(filters=None):
	_check()
	filters = frappe.parse_json(filters) if filters else {}
	from_date, to_date = _period(filters)
	values = {"f": from_date, "t": to_date}

	received = frappe.db.sql(
		"""select ifnull(sum(fees_received_amount), 0) as course, ifnull(sum(hostel_received_amount), 0) as hostel,
			ifnull(sum(vehicle_received_amount), 0) as transport, count(*) as n
		from `tabPayment Approval Log`
		where docstatus = 1 and payment_status = 'Approved' and ifnull(transaction_date, date) between %(f)s and %(t)s""",
		values,
		as_dict=True,
	)[0]
	days = frappe.db.sql(
		"""select ifnull(transaction_date, date) as d,
			sum(ifnull(fees_received_amount, 0) + ifnull(hostel_received_amount, 0) + ifnull(vehicle_received_amount, 0)) as amount
		from `tabPayment Approval Log`
		where docstatus = 1 and payment_status = 'Approved' and ifnull(transaction_date, date) between %(f)s and %(t)s
		group by d""",
		values,
		as_dict=True,
	)
	by_day = {str(r.d): flt(r.amount) for r in days}
	trend = [
		{"date": str(add_days(from_date, i)), "amount": by_day.get(str(add_days(from_date, i)), 0)}
		for i in range(date_diff(to_date, from_date) + 1)
	]
	modes = frappe.db.sql(
		"""select ifnull(mode_of_payment, 'Not set') as label,
			sum(ifnull(fees_received_amount, 0) + ifnull(hostel_received_amount, 0) + ifnull(vehicle_received_amount, 0)) as amount,
			count(*) as n
		from `tabPayment Approval Log`
		where docstatus = 1 and payment_status = 'Approved' and ifnull(transaction_date, date) between %(f)s and %(t)s
		group by label order by amount desc""",
		values,
		as_dict=True,
	)

	queue = [
		{"label": _("Payments to approve"), "doctype": "Payment Approval Log", "filters": {"docstatus": 0},
		 "n": frappe.db.count("Payment Approval Log", {"docstatus": 0})},
		{"label": _("Discounts to decide"), "doctype": "Discount Approval Log", "filters": {"docstatus": 0, "discount_status": "Pending"},
		 "n": frappe.db.count("Discount Approval Log", {"docstatus": 0, "discount_status": "Pending"})},
		{"label": _("Refunds to approve"), "doctype": "Fee Refund Request", "filters": {"status": "Requested"},
		 "n": frappe.db.count("Fee Refund Request", {"status": "Requested", "docstatus": 0})},
		{"label": _("Refunds to pay out"), "doctype": "Fee Refund Request", "filters": {"status": "Approved"},
		 "n": frappe.db.count("Fee Refund Request", {"status": "Approved", "docstatus": 0})},
		{"label": _("Transfers to approve"), "doctype": "Fee Transfer Request", "filters": {"docstatus": 0},
		 "n": frappe.db.count("Fee Transfer Request", {"docstatus": 0})},
	]

	outstanding = frappe.db.sql(
		"""select ifnull(sum(custom_course_balance), 0) as course, ifnull(sum(custom_hostel_balance), 0) as hostel,
			count(case when custom_course_balance > 0 then 1 end) as students
		from `tabProgram Enrollment` where docstatus = 1 and ifnull(custom_admission_status, '') not in ('Dropped', 'Cancelled')""",
		as_dict=True,
	)[0]
	overdue = frappe.db.sql(
		"""select pe.name as enrollment, pe.student_name, pe.program, min(fs.due_date) as since,
			sum(fs.final_amount - fs.paid_amount) as amount
		from `tabEnrollment Fee Schedule` fs
		inner join `tabProgram Enrollment` pe on pe.name = fs.parent and pe.docstatus = 1
		where fs.parenttype = 'Program Enrollment' and fs.status = 'Overdue'
		group by pe.name order by amount desc limit 8""",
		as_dict=True,
	)
	recent = frappe.db.sql(
		"""select name, student_name, ifnull(transaction_date, date) as d, mode_of_payment,
			ifnull(fees_received_amount, 0) + ifnull(hostel_received_amount, 0) + ifnull(vehicle_received_amount, 0) as amount
		from `tabPayment Approval Log` where docstatus = 1 and payment_status = 'Approved'
		order by modified desc limit 8""",
		as_dict=True,
	)
	total = flt(received.course) + flt(received.hostel) + flt(received.transport)
	return {
		"period": {"from_date": str(from_date), "to_date": str(to_date)},
		"kpis": {
			"total": total,
			"course": flt(received.course),
			"hostel": flt(received.hostel),
			"transport": flt(received.transport),
			"count": received.n,
			"outstanding": flt(outstanding.course),
			"hostel_outstanding": flt(outstanding.hostel),
			"students_owing": outstanding.students,
			"overdue": flt(
				frappe.db.sql(
					"""select sum(fs.final_amount - fs.paid_amount) from `tabEnrollment Fee Schedule` fs
					inner join `tabProgram Enrollment` pe on pe.name = fs.parent and pe.docstatus = 1
					where fs.parenttype = 'Program Enrollment' and fs.parentfield = 'custom_fee_schedule'
					and fs.status = 'Overdue'"""
				)[0][0]
			),
		},
		"trend": trend,
		"modes": [{"label": r.label, "n": flt(r.amount), "count": r.n} for r in modes],
		"queue": queue,
		"overdue": overdue,
		"recent": recent,
	}


# ----------------------------------------------------------------------------- admissions


@frappe.whitelist()
def admissions_dashboard(filters=None):
	_check()
	filters = frappe.parse_json(filters) if filters else {}
	from_date, to_date = _period(filters)
	cond = ["pe.docstatus = 1", "pe.enrollment_date between %(f)s and %(t)s"]
	values = {"f": from_date, "t": to_date}
	for key, col in (("center", "pe.custom_center"), ("vertical", "pe.custom_vertical")):
		if filters.get(key):
			cond.append(f"{col} = %({key})s")
			values[key] = filters[key]
	where = " and ".join(cond)

	k = frappe.db.sql(
		f"""select count(*) as total,
			sum(pe.custom_admission_status in ('Joined', 'Completed')) as joined,
			sum(ifnull(pe.custom_admission_status, 'Pending') = 'Pending') as pending,
			sum(pe.custom_admission_status in ('Dropped', 'Cancelled')) as dropped,
			sum(pe.custom_hosteller = 'Hosteller') as hostellers,
			ifnull(sum(pe.custom_final_amount), 0) as fee, ifnull(sum(pe.custom_course_paid), 0) as paid
		from `tabProgram Enrollment` pe where {where}""",
		values,
		as_dict=True,
	)[0]

	per_day = {
		str(r.d): r.n
		for r in frappe.db.sql(
			f"select pe.enrollment_date as d, count(*) as n from `tabProgram Enrollment` pe where {where} group by d",
			values,
			as_dict=True,
		)
	}
	span = date_diff(to_date, from_date) + 1
	if span > 62:
		# long periods read better by week (Monday starts)
		start = add_days(from_date, -getdate(from_date).weekday())
		trend, day = [], getdate(start)
		while day <= to_date:
			trend.append({"date": str(day), "count": sum(per_day.get(str(add_days(day, i)), 0) for i in range(7))})
			day = add_days(day, 7)
		bucket = "week"
	else:
		trend = [{"date": str(add_days(from_date, i)), "count": per_day.get(str(add_days(from_date, i)), 0)} for i in range(span)]
		bucket = "day"

	def group(col, limit=8):
		rows = frappe.db.sql(
			f"""select coalesce(nullif({col}, ''), 'Not set') as label, count(*) as n
			from `tabProgram Enrollment` pe where {where} group by label order by n desc""",
			values,
			as_dict=True,
		)
		if len(rows) > limit:
			rest = rows[limit - 1 :]
			rows = rows[: limit - 1] + [frappe._dict(label=_("Other"), n=sum(r.n for r in rest))]
		return rows

	waiting = frappe.db.sql(
		f"""select pe.name as enrollment, pe.student_name, pe.program, pe.enrollment_date, pe.custom_center as center,
			datediff(curdate(), pe.enrollment_date) as days
		from `tabProgram Enrollment` pe
		where {where} and ifnull(pe.custom_admission_status, 'Pending') = 'Pending'
		order by pe.enrollment_date asc limit 8""",
		values,
		as_dict=True,
	)
	overdue = frappe.db.sql(
		f"""select pe.name as enrollment, pe.student_name, pe.program, sum(fs.final_amount - fs.paid_amount) as amount
		from `tabEnrollment Fee Schedule` fs
		inner join `tabProgram Enrollment` pe on pe.name = fs.parent
		where {where} and fs.parentfield = 'custom_fee_schedule' and fs.status = 'Overdue'
		group by pe.name order by amount desc limit 6""",
		values,
		as_dict=True,
	)
	total = cint(k.total)
	return {
		"period": {"from_date": str(from_date), "to_date": str(to_date)},
		"kpis": {
			"total": total,
			"joined": cint(k.joined),
			"pending": cint(k.pending),
			"dropped": cint(k.dropped),
			"hostellers": cint(k.hostellers),
			"joined_pct": _pct(cint(k.joined), total),
			"fee": flt(k.fee),
			"paid": flt(k.paid),
			"paid_pct": _pct(flt(k.paid), flt(k.fee)),
		},
		"trend": trend,
		"bucket": bucket,
		"programs": group("pe.program"),
		"centers": group("pe.custom_center"),
		"stay": [
			{"label": _("Hostellers"), "n": cint(k.hostellers)},
			{"label": _("Day scholars"), "n": total - cint(k.hostellers)},
		],
		"waiting": waiting,
		"overdue": overdue,
	}


# ----------------------------------------------------------------------------- education


def _academic_year_start(today=None):
	"""The academic and financial year starts on 1 April."""
	t = getdate(today or nowdate())
	return getdate(f"{t.year if t.month >= 4 else t.year - 1}-04-01")


@frappe.whitelist()
def education_dashboard(filters=None):
	_check()
	filters = frappe.parse_json(filters) if filters else {}
	today = getdate(nowdate())
	ay_start = _academic_year_start(today)

	active = frappe.db.count("Student", {"enabled": 1})
	new_this_year = frappe.db.count("Student", {"enabled": 1, "joining_date": [">=", ay_start]})
	groups = frappe.db.count("Student Group", {"disabled": 0})
	instructors = frappe.db.count("Instructor", {"status": "Active"}) if frappe.get_meta("Instructor").has_field("status") else frappe.db.count("Instructor")
	running = frappe.db.sql(
		"""select count(distinct program) from `tabProgram Enrollment`
		where docstatus = 1 and ifnull(custom_admission_status, 'Pending') not in ('Dropped', 'Cancelled', 'Completed')"""
	)[0][0]

	att_today = frappe.db.sql(
		"""select sum(status = 'Present') as present, sum(status = 'Absent') as absent, count(*) as marked
		from `tabStudent Attendance` where docstatus = 1 and date = %s""",
		today,
		as_dict=True,
	)[0]
	start = add_days(today, -13)
	att_rows = {
		str(r.d): r
		for r in frappe.db.sql(
			"""select date as d, sum(status = 'Present') as present, count(*) as marked
			from `tabStudent Attendance` where docstatus = 1 and date between %s and %s group by date""",
			(start, today),
			as_dict=True,
		)
	}
	attendance = []
	for i in range(14):
		d = str(add_days(start, i))
		r = att_rows.get(d)
		attendance.append({"date": d, "rate": _pct(cint(r.present), cint(r.marked)) if r and r.marked else 0, "marked": cint(r.marked) if r else 0})

	def group(col):
		return frappe.db.sql(
			f"""select coalesce(nullif({col}, ''), 'Not set') as label, count(*) as n
			from `tabProgram Enrollment` pe
			where pe.docstatus = 1 and ifnull(pe.custom_admission_status, 'Pending') not in ('Dropped', 'Cancelled', 'Completed')
			group by label order by n desc limit 8""",
			as_dict=True,
		)

	student_groups = frappe.db.sql(
		"""select sg.name, sg.student_group_name, sg.program, sg.max_strength,
			(select count(*) from `tabStudent Group Student` s where s.parent = sg.name and ifnull(s.active, 1) = 1) as students,
			(select group_concat(i.instructor_name separator ', ') from `tabStudent Group Instructor` i where i.parent = sg.name) as instructors
		from `tabStudent Group` sg where sg.disabled = 0
		order by students desc limit 8""",
		as_dict=True,
	)
	recent = frappe.get_all(
		"Student",
		filters={"enabled": 1},
		fields=["name", "student_name", "joining_date", "custom_program"],
		order_by="joining_date desc, creation desc",
		limit_page_length=8,
	)
	low_attendance = frappe.db.sql(
		"""select sa.student, sa.student_name, sum(sa.status = 'Present') as present, count(*) as marked
		from `tabStudent Attendance` sa where sa.docstatus = 1 and sa.date between %s and %s
		group by sa.student
		having count(*) >= 3 and sum(sa.status = 'Present') / count(*) < 0.75
		order by sum(sa.status = 'Present') / count(*) asc limit 8""",
		(add_days(today, -29), today),
		as_dict=True,
	)
	for r in low_attendance:
		r.rate = _pct(cint(r.present), cint(r.marked))
	return {
		"year_start": str(ay_start),
		"kpis": {
			"active": active,
			"new_this_year": new_this_year,
			"running": running,
			"groups": groups,
			"instructors": instructors,
			"present_today": cint(att_today.present),
			"absent_today": cint(att_today.absent),
			"marked_today": cint(att_today.marked),
			"rate_today": _pct(cint(att_today.present), cint(att_today.marked)),
		},
		"attendance": attendance,
		"programs": group("pe.program"),
		"centers": group("pe.custom_center"),
		"groups": student_groups,
		"recent": recent,
		"low_attendance": low_attendance,
	}
