"""Import Future's "All Data.xlsx": masters, discounts and students (receipts come later).

Stages, each safe to run again (records are matched and updated, never duplicated):

  masters    Center, Hostel, Program, price chart (future.setup.import_masters)
  discounts  "Discount Master" -> Discount
  students   "Student Master"  -> Student (+ its Customer), matched on the Future student ID

Dry run by default: everything is rolled back and only the report is kept.

    bench --site <site> execute future.setup.import_all_data.run \
        --kwargs "{'path': '/path/All Data.xlsx', 'stage': 'students', 'dry_run': 1}"

On a hosted site, upload the workbook as a private File and call import_from_file (System
Manager); it runs in the background and get_import_status returns the report.
"""

import re

import frappe
from frappe.utils import cint, flt, getdate

from future.setup import import_masters as masters

STAGES = ("masters", "discounts", "students")
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
		else:
			import_students(wb, report, limit=limit, commit=not dry_run)
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
