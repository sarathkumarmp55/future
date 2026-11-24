"""Import Future's "All Data.xlsx": masters, discounts, students, enrollments and receipts.

Stages, in this order, each safe to run again (records are matched, never duplicated):

  masters      Center, Hostel, Program, price chart (future.setup.import_masters)
  discounts    "Discount Master" -> Discount
  students     "Student Master"  -> Student (+ its Customer), matched on the Future student ID
  enrollments  "Student Master"  -> submitted Program Enrollment with the course fee schedule and,
               for hostellers, the monthly hostel schedule (future.admissions), as an approved
               Payment Approval Log would create it
  receipts     "Invoice Data"    -> submitted Sales Invoice + Payment Entry per receipt, built the
               way Payment Approval Log builds them; matched on Sales Invoice.custom_import_key.
               future.admissions counts these invoices as payments.
  refresh      recompute every imported enrollment (paid amounts, balances, schedule status)

Dry run by default: everything is rolled back and only the report is kept. A receipts dry run
checks every row and posts the first `limit` (default 200) before rolling back.

    bench --site <site> execute future.setup.import_all_data.run \
        --kwargs "{'path': '/path/All Data.xlsx', 'stage': 'students', 'dry_run': 1}"

On a hosted site, upload the workbook as a private File and call import_from_file (System
Manager); it runs in the background and get_import_status returns the report.
"""

import hashlib
import re

import frappe
from frappe.utils import cint, flt, getdate

from future.future.doctype.payment_approval_log.payment_approval_log import set_inclusive_item_taxes
from future.setup import import_masters as masters

STAGES = ("masters", "discounts", "students", "enrollments", "receipts", "refresh")

# Receipt column -> fee item. "Course Fee" goes to the student's program item. GST follows each
# item's tax template, set from FEE_GST before the receipts are posted.
RECEIPT_COLUMNS = {
	"Course Fee": None,
	"Material Fee": "Material Fee",
	"Hostel Fee": "Hostel Fee",
	"Transportation Fee": "Transportation Fee",
	"Tab Fee": "Tablet Fee",
	"Tab Locking Fee": "Tab Locking Fee",
	"Mess Fee": "Mess Fee",
}
# GST confirmed by Future on 2026-11-24 (course, material 18% and hostel Non-GST are already set).
FEE_GST = {
	"Transportation Fee": "GST 18%",
	"Tablet Fee": "GST 18%",
	"Tab Locking Fee": "GST 18%",
	"Mess Fee": "GST 5%",
}

# (mode in the workbook, last digits of the bank account) -> (Mode of Payment, account number prefix)
PAYMENTS = {
	("upi", "560"): ("UPI (FEDERAL BANK)", "14130200028560"),
	("upi", "700"): ("UPI (HDFC BANK)", "99999995200700"),
	("pos", "700"): ("POS (HDFC BANK)", "99999995200700"),
	("pos", "560"): ("POS (HDFC BANK)", "14130200028560"),
	("cash", ""): ("Cash", None),
}
COMMIT_EVERY = 200
REPORT_LINES = 300


def _text(v):
	if v is None:
		return ""
	if isinstance(v, float) and v.is_integer():
		v = int(v)
	return re.sub(r"\s+", " ", str(v)).strip()


def _date(v):
	if not _text(v):
		return None
	try:
		return getdate(v)
	except Exception:
		return None


def _rows(wb, sheet, header_word):
	header, rows = masters._sheet(wb, sheet, header_word)
	return [{h: (r[i] if i < len(r) else None) for i, h in enumerate(header) if h} for r in rows]


class Report:
	def __init__(self, stage, dry_run):
		self.stage, self.dry_run = stage, dry_run
		self.counts, self.lines = {}, []

	def count(self, key, n=1):
		self.counts[key] = self.counts.get(key, 0) + n

	def note(self, line):
		self.count("notes")
		if len(self.lines) < REPORT_LINES:
			self.lines.append(line)

	def as_dict(self):
		return {"stage": self.stage, "dry_run": self.dry_run, "counts": self.counts, "notes": self.lines}


# ----------------------------------------------------------------------------- lookups


def _program_map(wb):
	"""Program name in the workbook -> Program on the site (same matching as the masters import)."""
	existing = frappe.get_all("Program", pluck="name")
	out = {}
	for r in _rows(wb, "Program Master", "Program Name"):
		name = _text(r.get("Program Name"))
		if name:
			match, proposed = masters._match_program(name, r.get("Academic Year"), existing)
			out[name] = match or (proposed if frappe.db.exists("Program", proposed) else None)
	return out


def _center_locations():
	return {c.name.lower(): c.location for c in frappe.get_all("Center", fields=["name", "location"])}


def _hostels():
	return {h.hostel_code: h.name for h in frappe.get_all("Hostel", fields=["name", "hostel_code"]) if h.hostel_code}


def _ensure(doctype, name, field):
	if name and not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, field: name}).insert(ignore_permissions=True)
	return name or None


# ----------------------------------------------------------------------------- discounts


def import_discounts(wb, report):
	programs = _program_map(wb)
	for r in _rows(wb, "Discount Master", "Discount ID"):
		code = _text(r.get("Discount ID"))
		if not code:
			continue
		program = programs.get(_text(r.get("Program")))
		if _text(r.get("Program")) and not program:
			report.note(f"{code}: program '{_text(r.get('Program'))}' not on the site")
		values = {
			"discount_amount": round(flt(r.get("Discount Amount")), 2),
			"percentage": _ensure("Percentage", _text(r.get("Matrix")), "percentage"),
			"base_of_discount": _ensure("Base of Discount", _text(r.get("Criteria")), "base_of_discount"),
		}
		if frappe.db.exists("Discount", code):
			doc = frappe.get_doc("Discount", code)
			changed = any(_text(doc.get(k)) != _text(v) for k, v in values.items())
			doc.update(values)
			if program and program not in [p.program for p in doc.program]:
				doc.append("program", {"program": program})
				changed = True
			if changed:
				doc.save(ignore_permissions=True)
				report.count("discounts updated")
			else:
				report.count("discounts unchanged")
		else:
			doc = frappe.get_doc({"doctype": "Discount", "discount_name": code, **values})
			if program:
				doc.append("program", {"program": program})
			doc.insert(ignore_permissions=True)
			report.count("discounts created")


# ----------------------------------------------------------------------------- students


def _student_values(r, programs, locations, hostels, report):
	code = _text(r.get("ID"))
	program_name = _text(r.get("Program"))
	program = programs.get(program_name)
	if program_name and not program:
		report.note(f"{code}: program '{program_name}' not on the site")
	centre = _text(r.get("Centre"))
	location = locations.get(centre.lower()) if centre else None
	if centre and not location:
		report.note(f"{code}: centre '{centre}' not on the site")
	hostel_code = _text(r.get("Hostel Code"))
	hostel = hostels.get(hostel_code)
	if hostel_code and not hostel:
		report.note(f"{code}: hostel '{hostel_code}' not on the site")
	discount = _text(r.get("Discount Id 1")) or _text(r.get("Discount Id 2"))
	if discount and not frappe.db.exists("Discount", discount):
		report.note(f"{code}: discount '{discount}' not on the site")
		discount = None

	dropped = cint(r.get("Is Dropped")) == 1
	joined = _text(r.get("Is Joined")).lower() == "joined"
	name = _text(r.get("Student Name"))
	values = {
		"first_name": name,
		"student_name": name,
		"student_email_id": _text(r.get("Student Email Address")).lower() or None,
		"student_mobile_number": _text(r.get("Student Mobile Number")) or None,
		"gender": _text(r.get("Gender")).title() or None,
		"joining_date": _date(r.get("Joining Date")),
		"enabled": 1 if joined and not dropped else 0,
		"date_of_leaving": _date(r.get("Date of Leaving")) if dropped else None,
		"reason_for_leaving": _text(r.get("Reason For Leaving")) if dropped else None,
		"address_line_1": _text(r.get("Address Line 1")) or _text(r.get("Address")) or None,
		"address_line_2": _text(r.get("Address Line 2")) or None,
		"pincode": _text(r.get("Pincode")) or None,
		"city": _text(r.get("City")) or None,
		"state": _text(r.get("State")) or None,
		"country": _text(r.get("Country")) if frappe.db.exists("Country", _text(r.get("Country"))) else None,
		"custom_student_code": code,
		"custom_program": program,
		"custom_academic_year": masters._academic_year(r.get("Academic Year")),
		"custom_preffered_centre": location,
		"custom_hostel": hostel,
		"custom_discount_id": discount,
		"custom_discount_applied": 1 if discount else 0,
		"custom_program_total_amount": flt(r.get("Final Offered")) or flt(r.get("Offered Amount")),
		"custom_guardian_mobile": _text(r.get("Guardian Mobile Number")) or None,
		"custom_sales_owner": " ".join(x for x in (_text(r.get("Sales Owner")), _text(r.get("Employee Name"))) if x)
		or None,
	}
	if not joined:
		report.count("students not joined (inactive)")
	if dropped:
		report.count("students dropped (inactive)")
	return code, values


def import_students(wb, report, limit=None, commit=False):
	programs, locations, hostels = _program_map(wb), _center_locations(), _hostels()
	existing = dict(
		frappe.get_all(
			"Student", filters={"custom_student_code": ["is", "set"]}, fields=["custom_student_code", "name"], as_list=True
		)
	)
	# Student email is unique; siblings and students in two programs share one.
	email_owner = {
		e.lower(): c
		for e, c in frappe.get_all(
			"Student", filters={"student_email_id": ["is", "set"]}, fields=["student_email_id", "custom_student_code"], as_list=True
		)
	}
	done = 0
	for r in _rows(wb, "Student Master", "Student Name"):
		if limit and done >= cint(limit):
			break
		code, values = _student_values(r, programs, locations, hostels, report)
		if not code or not values["first_name"]:
			report.note(f"Row without student ID or name skipped: {code or values['first_name']}")
			continue
		email = values["student_email_id"]
		if email and email_owner.setdefault(email, code) != code:
			report.note(f"{code}: email {email} already used by {email_owner[email]}; left blank")
			report.count("students with a shared email (left blank)")
			values["student_email_id"] = None
		name = existing.get(code)
		if name:
			doc = frappe.get_doc("Student", name)
			doc.update({k: v for k, v in values.items() if k not in ("first_name", "student_name")})
			doc.flags.ignore_validate = doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			report.count("students updated")
		else:
			# As the Payment Approval flow does: skip Student.validate (it creates a portal User).
			doc = frappe.get_doc({"doctype": "Student", **values})
			doc.flags.ignore_validate = doc.flags.ignore_mandatory = True
			doc.insert(ignore_permissions=True)  # on_update creates the Customer
			customer = frappe.db.get_value("Student", doc.name, "customer")
			frappe.db.set_value("Student", doc.name, "custom_student_customer", customer, update_modified=False)
			existing[code] = doc.name
			report.count("students created")
		done += 1
		if commit and done % COMMIT_EVERY == 0:
			frappe.db.commit()


# ----------------------------------------------------------------------------- receipts


def _amount(v):
	if isinstance(v, (int, float)):
		return flt(v)
	s = _text(v).replace(",", "")
	try:
		return flt(s)
	except Exception:
		return 0.0


def _import_key(r):
	raw = "|".join(
		_text(x)
		for x in (r.get("Student ID"), r.get("Transaction Date"), _amount(r.get("Total")), r.get("Reference No 1"), r.get("Reference No 2"))
	)
	return hashlib.md5(raw.encode()).hexdigest()


def _account(prefix, company):
	if prefix is None:
		return frappe.db.get_value("Account", {"account_type": "Cash", "is_group": 0, "company": company}, "name")
	return frappe.db.get_value("Account", {"name": ["like", f"{prefix}%"], "is_group": 0, "company": company}, "name")


def _payment_setup(company, report):
	"""Mode of Payment + account for each (mode, bank) pair; creates 'UPI (HDFC BANK)' if missing."""
	out = {}
	for key, (mode, prefix) in PAYMENTS.items():
		account = _account(prefix, company)
		if not account:
			report.note(f"No ledger for {key}: account {prefix or 'Cash'} not found")
			continue
		if not frappe.db.exists("Mode of Payment", mode):
			doc = frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mode, "type": "Cash" if prefix is None else "Bank", "enabled": 1})
			doc.append("accounts", {"company": company, "default_account": account})
			doc.insert(ignore_permissions=True)
			report.count("modes of payment created")
		out[key] = (mode, account)
	return out


def _payment_key(r):
	mode = _text(r.get("Mode of Payment")).lower()
	digits = re.findall(r"(\d{3})\s*$", _text(r.get("Bank")))
	return (mode, digits[0] if digits else "")


def _set_fee_gst(report):
	"""Give each fee item in FEE_GST exactly that Item Tax Template (creating the item if needed)."""
	for item, prefix in FEE_GST.items():
		masters._ensure_item(item, prefix)
		template = masters._tax_template(prefix)
		if not template:
			report.note(f"No Item Tax Template like '{prefix}' for {item}")
			continue
		doc = frappe.get_doc("Item", item)
		if [t.item_tax_template for t in doc.taxes] == [template]:
			continue
		doc.set("taxes", [{"item_tax_template": template}])
		doc.save(ignore_permissions=True)
		report.note(f"{item}: GST set to {template}")
		report.count("fee items GST updated")


def import_receipts(wb, report, limit=None, dry_run=1):
	company = frappe.defaults.get_global_default("company") or frappe.get_all("Company", pluck="name")[0]
	_set_fee_gst(report)
	payments = _payment_setup(company, report)
	students = {
		code: (name, customer, program)
		for code, name, customer, program in frappe.get_all(
			"Student",
			filters={"custom_student_code": ["is", "set"]},
			fields=["custom_student_code", "name", "customer", "custom_program"],
			as_list=True,
		)
	}
	posted = set(frappe.get_all("Sales Invoice", filters={"custom_import_key": ["is", "set"], "docstatus": 1}, pluck="custom_import_key"))
	limit = cint(limit) if limit else (200 if dry_run else 0)
	done = 0
	for r in _rows(wb, "Invoice Data", "Transaction Date"):
		code, key = _text(r.get("Student ID")), _import_key(r)
		report.count("receipts in file")
		if key in posted:
			report.count("receipts already posted")
			continue
		student = students.get(code)
		if not student:
			report.note(f"{code}: student not on the site (run the students stage first)")
			report.count("receipts skipped: unknown student")
			continue
		pay = payments.get(_payment_key(r))
		if not pay:
			report.note(f"{code}: no payment mapping for {_payment_key(r)}")
			report.count("receipts skipped: unknown payment mode")
			continue
		lines = []
		for column, item in RECEIPT_COLUMNS.items():
			amount = _amount(r.get(column))
			if amount:
				lines.append((item or student[2], amount))
		total = _amount(r.get("Total"))
		if not lines or not student[2] and any(i is None for i, _ in lines):
			report.note(f"{code}: nothing to invoice or no program on the student")
			report.count("receipts skipped: no lines")
			continue
		if abs(sum(a for _, a in lines) - total) > 1:
			report.note(f"{code}: fee columns add up to {sum(a for _, a in lines)}, Total is {total}")
		report.count("receipts ready")
		if limit and done >= limit:
			continue  # dry run: the rest are only checked
		frappe.db.savepoint("receipt")
		try:
			_post_receipt(r, student, lines, pay, key, company)
			report.count("receipts posted")
			posted.add(key)
			done += 1
		except Exception as e:
			frappe.db.rollback(save_point="receipt")
			report.count("receipts failed")
			report.note(f"{code} {_text(r.get('Reference No 1'))}: {str(e)[:300]}")
		if not dry_run and done and done % COMMIT_EVERY == 0:
			frappe.db.commit()


def _post_receipt(r, student, lines, pay, key, company):
	name, customer, _program = student
	date = getdate(r.get("Transaction Date"))
	ref1, ref2 = _text(r.get("Reference No 1")), _text(r.get("Reference No 2"))
	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": company,
			"student": name,
			"customer": customer,
			"posting_date": date,
			"set_posting_time": 1,
			"due_date": date,
			"custom_receipt_no": ref1 or ref2,
			"custom_import_key": key,
			"remarks": f"Imported receipt {ref1} {ref2}".strip(),
		}
	)
	for item, amount in lines:
		invoice.append("items", {"item_code": item, "qty": 1, "rate": amount})
	invoice.set_missing_values()
	set_inclusive_item_taxes(invoice)
	invoice.flags.ignore_permissions = True
	invoice.insert()
	invoice.submit()

	mode, account = pay
	payment = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"company": company,
			"posting_date": date,
			"mode_of_payment": mode,
			"party_type": "Customer",
			"party": customer,
			"paid_from": invoice.debit_to,
			"paid_to": account,
			"paid_amount": invoice.outstanding_amount,
			"received_amount": invoice.outstanding_amount,
			"reference_no": ref2 or ref1,
			"reference_date": date,
			"student": name,
			"remarks": f"Imported receipt {ref1} {ref2}".strip(),
		}
	)
	payment.append(
		"references",
		{
			"reference_doctype": "Sales Invoice",
			"reference_name": invoice.name,
			"total_amount": invoice.grand_total,
			"outstanding_amount": invoice.outstanding_amount,
			"allocated_amount": invoice.outstanding_amount,
		},
	)
	payment.flags.ignore_permissions = True
	payment.insert()
	payment.submit()


# ----------------------------------------------------------------------------- enrollments


def _receipt_dates(wb):
	"""First receipt date per student: the admission date when the workbook has no joining date."""
	first = {}
	for r in _rows(wb, "Invoice Data", "Transaction Date"):
		code, date = _text(r.get("Student ID")), _date(r.get("Transaction Date"))
		if date and (code not in first or date < first[code]):
			first[code] = date
		if _amount(r.get("Transportation Fee")):
			first.setdefault(f"transport:{code}", True)
	return first


def import_enrollments(wb, report, limit=None, commit=False):
	from future.admissions import build_course_schedule, build_hostel_schedule

	programs = _program_map(wb)
	centers = {c.lower(): c for c in frappe.get_all("Center", pluck="name")}
	hostels = {
		h.hostel_code: h for h in frappe.get_all("Hostel", fields=["name", "hostel_code", "hostel_type"]) if h.hostel_code
	}
	students = dict(
		frappe.get_all("Student", filters={"custom_student_code": ["is", "set"]}, fields=["custom_student_code", "name"], as_list=True)
	)
	enrolled = {
		(s, p)
		for s, p in frappe.get_all("Program Enrollment", filters={"docstatus": ["<", 2]}, fields=["student", "program"], as_list=True)
	}
	first = _receipt_dates(wb)
	done = 0
	for r in _rows(wb, "Student Master", "Student Name"):
		if limit and done >= cint(limit):
			break
		code = _text(r.get("ID"))
		student, program = students.get(code), programs.get(_text(r.get("Program")))
		if not student or not program:
			report.note(f"{code}: {'student' if not student else 'program'} not on the site")
			report.count("enrollments skipped")
			continue
		if (student, program) in enrolled:
			report.count("enrollments already there")
			continue

		dropped = cint(r.get("Is Dropped")) == 1
		joined = _text(r.get("Is Joined")).lower() == "joined"
		start = (
			_date(r.get("Joining Date"))
			or first.get(code)
			or frappe.db.get_value("Program", program, "custom_start_date")
			or getdate()
		)
		left = _date(r.get("Date of Leaving")) if dropped else None
		offered = flt(r.get("Offered Amount")) or flt(frappe.db.get_value("Program", program, "custom_selling_price"))
		discount_id = _text(r.get("Discount Id 1")) or _text(r.get("Discount Id 2"))
		discount_id = discount_id if discount_id and frappe.db.exists("Discount", discount_id) else None
		discount = max(flt(r.get("Discount Amount")) or (offered - flt(r.get("Final Offered"))), 0)

		hostel = hostels.get(_text(r.get("Hostel Code")))
		# Room type is not in the workbook yet (asked from Future); the hostel's own type or Non AC until then.
		room = ("AC" if hostel.hostel_type == "AC" else "Non AC") if hostel else None
		hostel_rows = build_hostel_schedule(program, room, start) if hostel else []
		if left:
			hostel_rows = [h for h in hostel_rows if getdate(h["due_date"]) < getdate(left)]

		center = centers.get(_text(r.get("Centre")).lower())
		location = frappe.db.get_value("Center", center, "location") if center else None
		pe = frappe.get_doc(
			{
				"doctype": "Program Enrollment",
				"student": student,
				"program": program,
				"academic_year": masters._academic_year(r.get("Academic Year"))
				or frappe.db.get_value("Program", program, "custom_academic_year"),
				"enrollment_date": start,
				"custom_center": center,
				"custom_location": location,
				"custom_admission_status": "Dropped" if dropped else "Joined" if joined else "Pending",
				"custom_has_joined": 1 if joined else 0,
				"custom_date_of_joined": _date(r.get("Joining Date")) if joined else None,
				"custom_offered_amount": offered,
				"custom_discount": discount_id,
				"custom_discount_amount": discount,
				"custom_hosteller": "Hosteller" if hostel else "Day Scholar",
				"custom_hostel": hostel.name if hostel else None,
				"custom_hostel_type": room,
				"custom_hostel_status": ("Vacated" if left else "Allotted") if hostel else None,
				"custom_hostel_joining_date": start if hostel else None,
				"custom_transport_required": 1 if first.get(f"transport:{code}") else 0,
				"custom_total_transport_fee": flt(frappe.db.get_value("Program", program, "custom_transport_fee"))
				if first.get(f"transport:{code}")
				else 0,
				"custom_fee_schedule": build_course_schedule(program, start, discount),
				"custom_hostel_schedule": hostel_rows,
			}
		)
		if hostel:
			pe.append("custom_hostel_log", {"hostel": hostel.name, "log_type": "Allotted", "room_type": room, "log_date": start, "notes": "Imported"})
			if left:
				pe.append("custom_hostel_log", {"hostel": hostel.name, "log_type": "Vacated", "room_type": room, "log_date": left, "notes": "Imported (dropped)"})
		pe.flags.ignore_permissions = pe.flags.ignore_mandatory = True
		frappe.db.savepoint("enrollment")
		try:
			pe.insert()
			pe.submit()
			enrolled.add((student, program))
			report.count("enrollments created")
			if hostel:
				report.count("hostellers (room type assumed until Future confirms)")
			done += 1
		except Exception as e:
			frappe.db.rollback(save_point="enrollment")
			report.count("enrollments failed")
			report.note(f"{code}: {str(e)[:300]}")
		if commit and done and done % COMMIT_EVERY == 0:
			frappe.db.commit()


def refresh_enrollments(report, commit=False):
	"""Recompute paid amounts, balances and schedule status of every imported student's enrollment."""
	from future.admissions import refresh_enrollment

	names = frappe.db.sql_list(
		"""select pe.name from `tabProgram Enrollment` pe join `tabStudent` s on s.name = pe.student
		where pe.docstatus = 1 and ifnull(s.custom_student_code, '') != ''"""
	)
	for i, name in enumerate(names, 1):
		refresh_enrollment(name)
		report.count("enrollments refreshed")
		if commit and i % COMMIT_EVERY == 0:
			frappe.db.commit()


# ----------------------------------------------------------------------------- entry points


def run(path, stage, dry_run=1, limit=None):
	import openpyxl

	if stage not in STAGES:
		frappe.throw(f"Stage must be one of {', '.join(STAGES)}")
	dry_run = cint(dry_run)
	if stage == "masters":
		return masters.run(path, dry_run=dry_run)

	wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
	report = Report(stage, dry_run)
	frappe.flags.mute_messages = True
	try:
		if stage == "discounts":
			import_discounts(wb, report)
		elif stage == "students":
			import_students(wb, report, limit=limit, commit=not dry_run)
		elif stage == "enrollments":
			import_enrollments(wb, report, limit=limit, commit=not dry_run)
		elif stage == "receipts":
			import_receipts(wb, report, limit=limit, dry_run=dry_run)
		else:
			refresh_enrollments(report, commit=not dry_run)
	except Exception:
		frappe.db.rollback()
		raise
	finally:
		frappe.flags.mute_messages = False
	if dry_run:
		frappe.db.rollback()
	else:
		frappe.db.commit()
	return report.as_dict()


def _run_job(file_url, stage, dry_run, limit=None):
	key = f"future_import:{stage}"
	frappe.cache.set_value(key, {"stage": stage, "status": "running"}, expires_in_sec=86400)
	try:
		path = frappe.get_doc("File", {"file_url": file_url}).get_full_path()
		result = run(path, stage, dry_run=dry_run, limit=limit)
		result["status"] = "done"
	except Exception:
		frappe.db.rollback()
		result = {"stage": stage, "status": "failed", "error": frappe.get_traceback()[-3000:]}
	frappe.cache.set_value(key, result, expires_in_sec=86400)


@frappe.whitelist()
def import_from_file(file_url, stage, dry_run=1, limit=None):
	"""Start a stage in the background (System Managers). Poll get_import_status for the report."""
	frappe.only_for("System Manager")
	if stage not in STAGES:
		frappe.throw(f"Stage must be one of {', '.join(STAGES)}")
	frappe.enqueue(
		"future.setup.import_all_data._run_job",
		queue="long",
		timeout=4 * 3600,
		file_url=file_url,
		stage=stage,
		dry_run=cint(dry_run),
		limit=limit,
	)
	return {"queued": stage, "dry_run": cint(dry_run)}


@frappe.whitelist()
def get_import_status(stage):
	frappe.only_for("System Manager")
	return frappe.cache.get_value(f"future_import:{stage}")
