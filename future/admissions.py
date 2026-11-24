"""Admissions: Program Enrollment as the admission record.

- An approved Payment Approval Log (from an Opportunity) creates the Student
  (existing code) and now also the Program Enrollment, with a course fee
  schedule built from the Program's price split and, for hostellers, a monthly
  hostel schedule from Admission Settings.
- Paid amounts are never typed in: `refresh_enrollment` rolls up every
  approved, submitted Payment Approval Log of the student and allocates it to
  the schedules (oldest due first), so balances and row statuses stay true.
- `get_enrollment_dashboard` feeds the 360 view on the enrollment form.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, get_first_day, getdate, nowdate

CLOSED_PAL = ("Rejected",)


def settings():
	return frappe.get_cached_doc("Admission Settings")


# ----------------------------------------------------------------------------- payments


def _pal_names_for(student):
	return frappe.db.sql_list(
		"""select name from `tabPayment Approval Log`
		where docstatus = 1 and payment_status = 'Approved' and (student = %(s)s or student_id = %(s)s)
		order by date, creation""",
		{"s": student},
	)


def _classify(item, table_category, s):
	if item and item == s.tablet_fee_item:
		return "tablet"
	if item and item == s.caution_deposit_item:
		return "caution"
	if item and item == s.transport_fee_item:
		return "transport"
	if item and item == s.hostel_fee_item:
		return "hostel"
	return table_category


def get_payments(student):
	"""Every approved payment line for `student`, classified into course / hostel / transport / tablet / caution."""
	s = settings()
	out = []
	tables = (("fee_details", "course"), ("hostel_components", "hostel"), ("vehicle_components", "transport"))
	for name in _pal_names_for(student):
		pal = frappe.get_doc("Payment Approval Log", name)
		for field, category in tables:
			for row in pal.get(field) or []:
				amount = flt(row.received_amount)
				if not amount:
					continue
				out.append(
					frappe._dict(
						log=pal.name,
						date=pal.transaction_date or pal.date,
						mode=pal.mode_of_payment,
						reference=pal.transaction_id,
						item=row.components,
						category=_classify(row.components, category, s),
						amount=amount,
					)
				)
	return out + _imported_payments(student, s)


# Items that count towards the course fee besides the program's own item.
COURSE_ITEMS = ("Registration Fee", "Material Fee", "Orientation Fee")


def _imported_payments(student, s):
	"""Receipts brought in from Future's records (future.setup.import_all_data): one submitted, paid
	Sales Invoice per receipt, with no Payment Approval Log behind it."""
	rows = frappe.db.sql(
		"""select si.name, si.posting_date, si.custom_receipt_no, sii.item_code, sii.amount,
			(select pe.mode_of_payment from `tabPayment Entry Reference` per
				join `tabPayment Entry` pe on pe.name = per.parent and pe.docstatus = 1
				where per.reference_doctype = 'Sales Invoice' and per.reference_name = si.name limit 1) as mode
		from `tabSales Invoice` si join `tabSales Invoice Item` sii on sii.parent = si.name
		where si.student = %s and si.docstatus = 1 and ifnull(si.custom_import_key, '') != ''
		order by si.posting_date, si.name, sii.idx""",
		student,
		as_dict=True,
	)
	out = []
	for r in rows:
		course = r.item_code in COURSE_ITEMS or frappe.db.exists("Program", r.item_code)
		out.append(
			frappe._dict(
				log=r.name,
				route="sales-invoice",
				date=r.posting_date,
				mode=r.mode,
				reference=r.custom_receipt_no,
				item=r.item_code,
				category=_classify(r.item_code, "course" if course else "other", s),
				amount=flt(r.amount),
			)
		)
	return out


# ----------------------------------------------------------------------------- schedules


def _allocate(rows, paid, today):
	"""Spread `paid` over schedule rows by due date; set paid_amount and status in place."""
	for row in sorted(rows, key=lambda r: (getdate(r.due_date) if r.due_date else getdate("2999-12-31"), r.idx)):
		row.final_amount = flt(row.amount) - flt(row.discount_amount)
		row.paid_amount = min(paid, row.final_amount) if paid > 0 else 0
		paid -= row.paid_amount
		if row.paid_amount >= row.final_amount and row.final_amount > 0:
			row.status = "Paid"
		elif row.due_date and getdate(row.due_date) < today:
			row.status = "Overdue"
		elif row.paid_amount > 0:
			row.status = "Partly Paid"
		else:
			row.status = "Unpaid"


CATEGORY_KEY = {
	"Course Fee": "course",
	"Hostel Fee": "hostel",
	"Transportation Fee": "transport",
	"Tablet Fee": "tablet",
	"Caution Deposit": "caution",
}


def get_adjustments(enrollment):
	"""Paid refunds and approved transfers touching `enrollment`, as signed amounts per category."""
	out = []
	if not enrollment:
		return out
	for r in frappe.get_all(
		"Fee Refund Request",
		filters={"enrollment": enrollment, "docstatus": 1, "status": "Paid"},
		fields=["name", "category", "amount", "reference_date", "modified"],
	):
		out.append(frappe._dict(kind="Refund", doc=r.name, category=CATEGORY_KEY[r.category], amount=-flt(r.amount), date=r.reference_date or r.modified))
	for t in frappe.get_all(
		"Fee Transfer Request",
		filters={"docstatus": 1},
		or_filters={"from_enrollment": enrollment, "to_enrollment": enrollment},
		fields=["name", "transfer_type", "from_enrollment", "to_enrollment", "from_category", "to_category", "amount", "modified"],
	):
		target = t.from_enrollment if t.transfer_type == "Self" else t.to_enrollment
		if t.from_enrollment == enrollment:
			out.append(frappe._dict(kind="Transfer Out", doc=t.name, category=CATEGORY_KEY[t.from_category], amount=-flt(t.amount), date=t.modified))
		if target == enrollment:
			out.append(frappe._dict(kind="Transfer In", doc=t.name, category=CATEGORY_KEY[t.to_category], amount=flt(t.amount), date=t.modified))
	return out


def category_sums(doc, payments=None, adjustments=None):
	payments = get_payments(doc.student) if payments is None else payments
	adjustments = get_adjustments(doc.name) if adjustments is None else adjustments
	sums = {}
	for p in payments:
		sums[p.category] = sums.get(p.category, 0) + p.amount
	for a in adjustments:
		sums[a.category] = sums.get(a.category, 0) + a.amount
	return sums


@frappe.whitelist()
def get_available(enrollment, category):
	"""Money paid into `category` on `enrollment` that can still be refunded or transferred."""
	doc = frappe.get_doc("Program Enrollment", enrollment)
	doc.check_permission("read")
	return max(flt(category_sums(doc).get(CATEGORY_KEY[category], 0)), 0)


def compute(doc, payments=None):
	"""Fill every derived amount on a Program Enrollment `doc` (not saved)."""
	payments = get_payments(doc.student) if payments is None else payments
	adjustments = get_adjustments(doc.name) if not doc.is_new() else []
	sums = category_sums(doc, payments, adjustments)
	doc.custom_refunded_amount = -sum(a.amount for a in adjustments if a.kind == "Refund")

	doc.custom_final_amount = flt(doc.custom_offered_amount) - flt(doc.custom_discount_amount)
	today = getdate(nowdate())
	_allocate(doc.get("custom_fee_schedule") or [], sums.get("course", 0), today)
	_allocate(doc.get("custom_hostel_schedule") or [], sums.get("hostel", 0), today)
	doc.custom_total_hostel_fee = sum(flt(r.final_amount) for r in doc.get("custom_hostel_schedule") or [])

	course_due = doc.custom_final_amount or sum(flt(r.final_amount) for r in doc.get("custom_fee_schedule") or [])
	doc.custom_course_paid = sums.get("course", 0)
	doc.custom_course_balance = max(course_due - doc.custom_course_paid, 0)
	doc.custom_hostel_paid = sums.get("hostel", 0)
	doc.custom_hostel_balance = max(flt(doc.custom_total_hostel_fee) - doc.custom_hostel_paid, 0)
	doc.custom_transport_paid = sums.get("transport", 0)
	doc.custom_tablet_paid = sums.get("tablet", 0)
	doc.custom_caution_deposit = sums.get("caution", 0)
	doc.custom_other_paid = sums.get("other", 0)
	return payments


def refresh_enrollment(name):
	"""Recompute and store derived amounts, including on a submitted enrollment."""
	doc = frappe.get_doc("Program Enrollment", name)
	compute(doc)
	fields = (
		"custom_final_amount custom_total_hostel_fee custom_course_paid custom_course_balance custom_hostel_paid "
		"custom_hostel_balance custom_transport_paid custom_tablet_paid custom_caution_deposit custom_other_paid "
		"custom_refunded_amount"
	).split()
	doc.db_set({f: doc.get(f) for f in fields}, update_modified=False)
	for table in ("custom_fee_schedule", "custom_hostel_schedule"):
		for row in doc.get(table) or []:
			row.db_set(
				{"final_amount": row.final_amount, "paid_amount": row.paid_amount, "status": row.status},
				update_modified=False,
			)
	_sync_student(doc)


def _sync_student(doc):
	"""Keep the Student's legacy fee summary fields in step with the enrollment."""
	frappe.db.set_value(
		"Student",
		doc.student,
		{
			"custom_program_total_amount": doc.custom_final_amount,
			"custom_program_total_received_amount": doc.custom_course_paid,
			"custom_program_balance_amount": doc.custom_course_balance,
			"custom_hostel_total_amount": doc.custom_total_hostel_fee,
			"custom_hostel_total_received_amount": doc.custom_hostel_paid,
			"custom_hostel_balance_amount": doc.custom_hostel_balance,
		},
		update_modified=False,
	)


def refresh_student_enrollments(student):
	for name in frappe.get_all("Program Enrollment", filters={"student": student, "docstatus": ["<", 2]}, pluck="name"):
		refresh_enrollment(name)


def build_course_schedule(program, start_date, discount=0):
	"""Registration / material / orientation due at admission, course fee in instalments."""
	p = frappe.get_cached_doc("Program", program)
	s = settings()
	start = getdate(start_date or nowdate())
	rows = []
	for label, field in (("Registration Fee", "custom_reg_fee"), ("Material Fee", "custom_material_fee"), ("Orientation Fee", "custom_orientation_fee")):
		amount = flt(p.get(field))
		if amount and frappe.db.exists("Item", label):
			rows.append({"component": label, "due_date": start, "amount": amount})

	course = flt(p.get("custom_course_fee"))
	course_item = program if frappe.db.exists("Item", program) else None
	if course and course_item:
		n = max(cint(s.course_installments) or 3, 1)
		gap = cint(s.installment_gap_days) or 45
		share, disc = round(course / n, 2), round(flt(discount) / n, 2)
		for i in range(n):
			last = i == n - 1
			rows.append(
				{
					"component": course_item,
					"due_date": add_days(start, gap * i),
					"amount": round(course - share * (n - 1), 2) if last else share,
					"discount_amount": round(flt(discount) - disc * (n - 1), 2) if last else disc,
				}
			)
	elif not rows:
		# Programs without a price split: one row per Program component.
		for c in p.get("custom_fees_details") or []:
			rows.append({"component": c.component, "due_date": start, "amount": flt(c.amount_with_gst) or flt(c.amount)})
	return rows


def hostel_rate(program, hostel_type):
	s = settings()
	p = frappe.get_cached_doc("Program", program)
	applies = "FSP Plus Two" if (p.custom_vertical == "FSP" and "plus two" in (program or "").lower()) else "Others"
	for r in s.hostel_rates or []:
		if r.applies_to == applies:
			return flt(r.ac_monthly if hostel_type == "AC" else r.non_ac_monthly)
	return 0


def build_hostel_schedule(program, hostel_type, start_date, months=None):
	s = settings()
	rate = hostel_rate(program, hostel_type)
	item = s.hostel_fee_item or ("Hostel Fee" if frappe.db.exists("Item", "Hostel Fee") else None)
	if not rate or not item:
		return []
	months = cint(months) or cint(s.hostel_months) or 10
	first = add_days(get_first_day(getdate(start_date or nowdate())), 4)  # the 5th, as in the hostel fee sheet
	end = frappe.db.get_value("Program", program, "custom_end_date")
	rows = []
	for i in range(months):
		due = add_months(first, i)
		if end and getdate(due) > getdate(end):
			break  # no hostel fee after the program ends
		rows.append({"component": item, "due_date": due, "amount": rate})
	return rows


# ----------------------------------------------------------------------------- Program Enrollment hooks


def enrollment_validate(doc, method=None):
	if doc.custom_hosteller != "Hosteller":
		doc.custom_hostel = doc.custom_hostel_type = None
	if doc.custom_has_joined and not doc.custom_date_of_joined:
		doc.custom_date_of_joined = nowdate()
	if doc.custom_has_joined and doc.custom_admission_status == "Pending":
		doc.custom_admission_status = "Joined"
	compute(doc)


def enrollment_after_submit_update(doc, method=None):
	refresh_enrollment(doc.name)


@frappe.whitelist()
def make_schedules(name):
	"""Button on the form: (re)build the default schedules for a draft or submitted enrollment."""
	doc = frappe.get_doc("Program Enrollment", name)
	doc.check_permission("write")
	doc.set("custom_fee_schedule", build_course_schedule(doc.program, doc.enrollment_date, doc.custom_discount_amount))
	if doc.custom_hosteller == "Hosteller":
		doc.set(
			"custom_hostel_schedule",
			build_hostel_schedule(doc.program, doc.custom_hostel_type, doc.custom_hostel_joining_date or doc.enrollment_date),
		)
	doc.flags.ignore_validate_update_after_submit = True
	doc.save()
	return doc.name


# ----------------------------------------------------------------------------- Payment Approval Log hooks


def _discount_amount(discount_id, offered):
	if not discount_id:
		return 0
	d = frappe.db.get_value("Discount", discount_id, ["discount_amount", "percentage"], as_dict=True) or {}
	if flt(d.get("discount_amount")):
		return flt(d.discount_amount)
	pct = frappe.db.get_value("Percentage", d.get("percentage"), "percentage") if d.get("percentage") else 0
	return round(flt(offered) * flt(str(pct or 0).strip("%")) / 100, 2)


def create_enrollment_from_pal(pal):
	student = frappe.db.get_value("Payment Approval Log", pal.name, "student") or pal.student_id
	if not student or not pal.program or not frappe.db.exists("Student", student):
		return None
	existing = frappe.db.get_value(
		"Program Enrollment", {"student": student, "program": pal.program, "docstatus": ["<", 2]}, "name"
	)
	if existing:
		return existing

	academic_year = pal.academic_year or frappe.db.get_value("Program", pal.program, "custom_academic_year")
	offered = flt(pal.total_amount) or flt(frappe.db.get_value("Program", pal.program, "custom_selling_price"))
	discount = _discount_amount(pal.discount_id, offered) if cint(pal.discount_applied) else 0
	start = pal.date or nowdate()
	center = None
	if pal.location:
		# prefer the main campus of that location over schools and crash centres
		centers = frappe.get_all(
			"Center", filters={"location": pal.location, "is_active": 1}, fields=["name", "center_type"]
		)
		rank = {"Campus": 0, "School": 1, "Crash Course": 2}
		centers.sort(key=lambda c: rank.get(c.center_type, 3))
		center = centers[0].name if centers else None
	hosteller = "Hosteller" if (cint(pal.hostel_required) or pal.hostel) else "Day Scholar"
	hostel_type = None
	if pal.hostel:
		hostel_type = "AC" if frappe.db.get_value("Hostel", pal.hostel, "hostel_type") == "AC" else "Non AC"

	pe = frappe.get_doc(
		{
			"doctype": "Program Enrollment",
			"student": student,
			"program": pal.program,
			"academic_year": academic_year,
			"enrollment_date": start,
			"custom_payment_approvallog": pal.name,
			"custom_lead": pal.lead_reference,
			"custom_opportunity": pal.opportunity_reference,
			"custom_center": center,
			"custom_admission_status": "Pending",
			"custom_offered_amount": offered,
			"custom_discount": pal.discount_id if cint(pal.discount_applied) else None,
			"custom_discount_amount": discount,
			"custom_hosteller": hosteller,
			"custom_hostel": pal.hostel,
			"custom_hostel_type": hostel_type,
			"custom_hostel_status": "Allotted" if pal.hostel else None,
			"custom_hostel_joining_date": start if pal.hostel else None,
			"custom_transport_required": 1 if (cint(pal.vehicle_required) or pal.vehicle) else 0,
			"custom_vehicle": pal.vehicle,
			"custom_total_transport_fee": flt(pal.vehicle_total_amount),
			"custom_fee_schedule": build_course_schedule(pal.program, start, discount),
			"custom_hostel_schedule": build_hostel_schedule(pal.program, hostel_type, start) if pal.hostel else [],
		}
	)
	if pal.hostel:
		from future.hostel_management import check_capacity

		try:
			check_capacity(pal.hostel, hostel_type or "Non AC")
		except frappe.ValidationError as e:
			frappe.clear_last_message()
			frappe.msgprint(
				_("Hostel allotted anyway because the payment is approved, but: {0}").format(e),
				indicator="orange",
				title=_("Hostel capacity"),
			)
		pe.append(
			"custom_hostel_log",
			{
				"hostel": pal.hostel,
				"log_type": "Allotted",
				"room_type": hostel_type,
				"log_date": start,
				"notes": _("Allotted on admission ({0})").format(pal.name),
				"logged_by": frappe.session.user,
			},
		)
	pe.flags.ignore_permissions = True
	pe.flags.ignore_mandatory = True
	pe.insert()
	pe.submit()
	return pe.name


def on_pal_submit(doc, method=None):
	if doc.payment_status != "Approved":
		return
	if cint(doc.from_opportunity):
		name = create_enrollment_from_pal(doc)
		if name:
			frappe.msgprint(
				_("Program Enrollment {0} created.").format(frappe.get_desk_link("Program Enrollment", name)),
				indicator="green",
				alert=True,
			)
	student = frappe.db.get_value("Payment Approval Log", doc.name, "student") or doc.student_id
	if student and frappe.db.exists("Student", student):
		refresh_student_enrollments(student)


def on_pal_cancel(doc, method=None):
	student = doc.student or doc.student_id
	if student and frappe.db.exists("Student", student):
		refresh_student_enrollments(student)


# ----------------------------------------------------------------------------- dashboard


@frappe.whitelist()
def get_enrollment_dashboard(name):
	doc = frappe.get_doc("Program Enrollment", name)
	doc.check_permission("read")
	payments = compute(doc)
	student = frappe.db.get_value(
		"Student",
		doc.student,
		["student_name", "student_mobile_number", "student_email_id", "image", "custom_app_access_provided"],
		as_dict=True,
	) or {}

	def pct(part, whole):
		return round(flt(part) * 100 / flt(whole)) if flt(whole) else 0

	course_total = flt(doc.custom_final_amount) or sum(flt(r.final_amount) for r in doc.custom_fee_schedule or [])
	next_due = next(
		(
			r
			for r in sorted(doc.custom_fee_schedule or [], key=lambda r: str(r.due_date or ""))
			if r.status in ("Unpaid", "Partly Paid", "Overdue")
		),
		None,
	)
	overdue = sum(
		flt(r.final_amount) - flt(r.paid_amount)
		for r in list(doc.custom_fee_schedule or []) + list(doc.custom_hostel_schedule or [])
		if r.status == "Overdue"
	)
	discount_filters = [["Discount Approval Log", "student", "=", doc.student]]
	if doc.custom_opportunity:
		discount_filters = [["Discount Approval Log", "opportunity_reference", "=", doc.custom_opportunity]]
	discounts = frappe.get_all(
		"Discount Approval Log",
		or_filters=discount_filters + [["Discount Approval Log", "student", "=", doc.student]],
		fields=["name", "discount_id", "amount", "discount_status", "base_of_discount", "creation"],
		order_by="creation desc",
	)
	refunds = frappe.get_all(
		"Fee Refund Request",
		filters={"enrollment": doc.name, "docstatus": ["<", 2]},
		fields=["name", "category", "amount", "status", "creation"],
		order_by="creation desc",
	)
	transfers = [
		{"name": a.doc, "kind": a.kind, "category": a.category, "amount": a.amount}
		for a in get_adjustments(doc.name)
		if a.kind != "Refund"
	]
	pending_transfers = frappe.get_all(
		"Fee Transfer Request",
		filters={"docstatus": 0},
		or_filters={"from_enrollment": doc.name, "to_enrollment": doc.name},
		fields=["name", "from_category", "to_category", "amount"],
	)
	def schedule(rows):
		out = []
		for r in sorted(rows or [], key=lambda r: str(r.due_date or "")):
			label = frappe.db.get_value("Item", r.component, "item_name") or r.component
			out.append(
				{
					"label": "Course fee" if r.component == doc.program else label,
					"due_date": r.due_date,
					"amount": flt(r.final_amount),
					"paid": flt(r.paid_amount),
					"status": r.status,
				}
			)
		return out

	return {
		"course_schedule": schedule(doc.custom_fee_schedule),
		"hostel_schedule": schedule(doc.custom_hostel_schedule),
		"discounts": discounts,
		"refunds": refunds,
		"transfers": transfers,
		"pending_transfers": pending_transfers,
		"tablets": [
			{"tablet_id": t.tablet_id, "model": t.model_number, "allocated_on": t.allocated_on, "returned_on": t.returned_on, "condition": t.condition}
			for t in doc.get("custom_tablets") or []
		],
		"student": {"id": doc.student, **student},
		"enrollment": {
			"name": doc.name,
			"program": doc.program,
			"academic_year": doc.academic_year,
			"date": doc.enrollment_date,
			"batch": doc.student_batch_name,
			"center": doc.custom_center,
			"program_type": doc.custom_program_type,
			"vertical": doc.custom_vertical,
			"status": doc.custom_admission_status,
			"docstatus": doc.docstatus,
			"hosteller": doc.custom_hosteller,
			"hostel": frappe.db.get_value("Hostel", doc.custom_hostel, "hostel_name") or doc.custom_hostel if doc.custom_hostel else None,
			"hostel_type": doc.custom_hostel_type,
			"joined_on": doc.custom_date_of_joined,
			"discount": doc.custom_discount,
		},
		"course": {
			"offered": flt(doc.custom_offered_amount),
			"discount": flt(doc.custom_discount_amount),
			"total": course_total,
			"paid": flt(doc.custom_course_paid),
			"balance": flt(doc.custom_course_balance),
			"pct": pct(doc.custom_course_paid, course_total),
			"next_due": {"date": next_due.due_date, "amount": flt(flt(next_due.final_amount) - flt(next_due.paid_amount), 2)}
			if next_due
			else None,
		},
		"hostel": {
			"total": flt(doc.custom_total_hostel_fee),
			"paid": flt(doc.custom_hostel_paid),
			"balance": flt(doc.custom_hostel_balance),
			"pct": pct(doc.custom_hostel_paid, doc.custom_total_hostel_fee),
		},
		"extras": {
			"transport": flt(doc.custom_transport_paid),
			"tablet": flt(doc.custom_tablet_paid),
			"caution": flt(doc.custom_caution_deposit),
			"refunded": flt(doc.custom_refunded_amount),
		},
		"overdue": flt(overdue, 2),
		"payments": [
			{**p, "category": _(p.category.title())} for p in sorted(payments, key=lambda p: str(p.date or ""), reverse=True)
		],
	}


def refresh_overdue():
	"""Daily: re-derive schedule statuses for enrollments with an unpaid row whose due date has passed."""
	names = frappe.db.sql_list(
		"""select distinct fs.parent from `tabEnrollment Fee Schedule` fs
		inner join `tabProgram Enrollment` pe on pe.name = fs.parent and pe.docstatus = 1
		where fs.parenttype = 'Program Enrollment' and fs.status in ('Unpaid', 'Partly Paid') and fs.due_date < %s""",
		nowdate(),
	)
	for name in names:
		refresh_enrollment(name)
