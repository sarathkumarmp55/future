"""Import Future's "All Data.xlsx": masters, discounts, students, receipts and balances.

Stages, in this order, each safe to run again (records are matched, never duplicated):

  masters    Center, Hostel, Program, price chart (future.setup.import_masters)
  discounts  "Discount Master" -> Discount
  students   "Student Master"  -> Student (+ its Customer), matched on the Future student ID
  receipts   "Invoice Data"    -> submitted Sales Invoice + Payment Entry per receipt, built
             the way Payment Approval Log builds them; matched on Sales Invoice.custom_import_key
  balances   per student: program / hostel / transport amounts received and balance

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

STAGES = ("masters", "discounts", "students", "receipts", "balances")

# Receipt column -> fee item. "Course Fee" goes to the student's program item. GST follows each
# item's tax template (Material 18%, Hostel / Transport / Tablet Non-GST on the site today).
RECEIPT_COLUMNS = {
	"Course Fee": None,
	"Material Fee": "Material Fee",
	"Hostel Fee": "Hostel Fee",
	"Transportation Fee": "Transportation Fee",
	"Tab Fee": "Tablet Fee",
	"Tab Locking Fee": "Tab Locking Fee",
	"Mess Fee": "Mess Fee",
}
NEW_FEE_ITEMS = {"Tab Locking Fee": "Non-GST", "Mess Fee": "Non-GST"}  # GST to be confirmed by Future
PROGRAM_COLUMNS = ("Course Fee", "Material Fee")  # Selling Price = Reg + Material + Orientation + Course
HOSTEL_COLUMNS = ("Hostel Fee",)
TRANSPORT_COLUMNS = ("Transportation Fee",)

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


def import_receipts(wb, report, limit=None, dry_run=1):
	company = frappe.defaults.get_global_default("company") or frappe.get_all("Company", pluck="name")[0]
	for item, tax in NEW_FEE_ITEMS.items():
		masters._ensure_item(item, tax)
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


# ----------------------------------------------------------------------------- balances


def import_balances(wb, report):
	"""Amounts received per student from the receipts sheet; program balance = Final Offered - received.

	Hostel and transport totals are not in the workbook, so only what was received is set."""
	received = {}
	for r in _rows(wb, "Invoice Data", "Transaction Date"):
		code = _text(r.get("Student ID"))
		got = received.setdefault(code, [0.0, 0.0, 0.0])
		got[0] += sum(_amount(r.get(c)) for c in PROGRAM_COLUMNS)
		got[1] += sum(_amount(r.get(c)) for c in HOSTEL_COLUMNS)
		got[2] += sum(_amount(r.get(c)) for c in TRANSPORT_COLUMNS)
	for code, name, total in frappe.get_all(
		"Student",
		filters={"custom_student_code": ["is", "set"]},
		fields=["custom_student_code", "name", "custom_program_total_amount"],
		as_list=True,
	):
		program, hostel, transport = received.get(code, (0.0, 0.0, 0.0))
		balance = flt(total) - program
		if balance < -1:
			report.note(f"{code}: paid {program} towards the program, more than its total {flt(total)}")
			report.count("students paid more than the program total")
		frappe.db.set_value(
			"Student",
			name,
			{
				"custom_program_total_received_amount": program,
				"custom_program_balance_amount": balance,
				"custom_hostel_total_received_amount": hostel,
				"custom_vehicle_total_received_amount": transport,
			},
			update_modified=False,
		)
		report.count("students updated")


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
		elif stage == "receipts":
			import_receipts(wb, report, limit=limit, dry_run=dry_run)
		else:
			import_balances(wb, report)
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
