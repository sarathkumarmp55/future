"""Bring the live HR masters and employees in line with Future's HR workbooks.

Reads (from ~/Downloads unless --dir is given):
  Work Force - HR - Master Data New.xlsx   Master (employees) + Data Set (designation list)
  Payroll Master.xlsx                      payroll group, salary band, PF/ESI/LWF applicability, CTC, bank
  Statutory Tracker.xlsx                   ESIC, UAN, LWF numbers

Talks to the site over its REST API, so it works without a deploy. Dry run by default:
writes a report workbook of every change and touches nothing. --apply makes the changes.

  FUTURE_URL=https://erp.edfuture.in FUTURE_TOKEN=key:secret python3 scripts/hr_sync.py
  FUTURE_URL=... FUTURE_TOKEN=... python3 scripts/hr_sync.py --apply

The token is read from the environment only; never put it in this file.
"""

import argparse
import collections
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import openpyxl

COMPANY_ABBR = "ED"

# Employee custom fields owned by the future app (also in future/future/custom/employee.json).
CUSTOM_FIELDS = [
	{"fieldname": "custom_statutory_section", "fieldtype": "Section Break", "label": "Statutory (Future)", "insert_after": "ifsc_code", "collapsible": 1},
	{"fieldname": "custom_aadhaar_number", "fieldtype": "Data", "label": "Aadhaar Number", "insert_after": "custom_statutory_section"},
	{"fieldname": "custom_uan_number", "fieldtype": "Data", "label": "UAN (PF)", "insert_after": "custom_aadhaar_number"},
	{"fieldname": "custom_esic_number", "fieldtype": "Data", "label": "ESIC Number", "insert_after": "custom_uan_number"},
	{"fieldname": "custom_lwf_number", "fieldtype": "Data", "label": "LWF Number", "insert_after": "custom_esic_number"},
	{"fieldname": "custom_statutory_cb", "fieldtype": "Column Break", "insert_after": "custom_lwf_number"},
	{"fieldname": "custom_pf_applicable", "fieldtype": "Check", "label": "PF Applicable", "insert_after": "custom_statutory_cb"},
	{"fieldname": "custom_esi_applicable", "fieldtype": "Check", "label": "ESI Applicable", "insert_after": "custom_pf_applicable"},
	{"fieldname": "custom_lwf_applicable", "fieldtype": "Check", "label": "LWF Applicable", "insert_after": "custom_esi_applicable"},
	{"fieldname": "custom_payroll_group", "fieldtype": "Select", "label": "Payroll Group", "options": "\nStaff\nApprentice\nConsultant", "insert_after": "grade", "in_standard_filter": 1},
	{"fieldname": "custom_salary_band", "fieldtype": "Data", "label": "Salary Band", "insert_after": "custom_payroll_group"},
	{"fieldname": "custom_work_location", "fieldtype": "Data", "label": "Work Location", "insert_after": "branch"},
	{"fieldname": "custom_sub_department", "fieldtype": "Data", "label": "Function / Sub-department", "insert_after": "department"},
	{"fieldname": "custom_father_name", "fieldtype": "Data", "label": "Father's Name", "insert_after": "date_of_birth"},
	{"fieldname": "custom_old_employee_code", "fieldtype": "Data", "label": "Old Employee Code", "insert_after": "employee_number", "read_only": 1},
]

BRANCH_MAP = {"kozhikode-ho": "Kozhikode - HO", "kozhikode - ho": "Kozhikode - HO"}
DEPARTMENT_MAP = {"human resource": "Human Resources"}  # reuse the existing ERPNext department
BLOOD = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
# Already filled on the site and possibly more accurate there: never overwritten, differences listed for HR.
KEEP_IF_SET = ("first_name", "date_of_birth")
REQUIRED = ("first_name", "gender", "date_of_birth", "date_of_joining")


# ----------------------------------------------------------------------------- site API


class Site:
	def __init__(self, url, token):
		self.url = url.rstrip("/")
		self.headers = {"Authorization": f"token {token}", "Content-Type": "application/json", "Accept": "application/json"}
		if os.environ.get("FUTURE_HOST"):  # local testing: site name when the URL is an IP
			self.headers["Host"] = os.environ["FUTURE_HOST"]

	def _call(self, method, path, data=None):
		req = urllib.request.Request(
			self.url + path,
			data=json.dumps(data).encode() if data is not None else None,
			headers=self.headers,
			method=method,
		)
		try:
			with urllib.request.urlopen(req, timeout=60) as r:
				return json.loads(r.read() or b"{}")
		except urllib.error.HTTPError as e:
			body = e.read().decode(errors="replace")
			try:
				msg = json.loads(body)
				msg = msg.get("exception") or msg.get("_server_messages") or body
			except Exception:
				msg = body
			raise RuntimeError(f"{method} {path}: {e.code} {str(msg)[:400]}") from None

	def get_all(self, doctype, fields=("name",), filters=None):
		q = {"fields": json.dumps(list(fields)), "limit_page_length": 0}
		if filters:
			q["filters"] = json.dumps(filters)
		return self._call("GET", f"/api/resource/{urllib.parse.quote(doctype)}?{urllib.parse.urlencode(q)}")["data"]

	def insert(self, doc):
		return self._call("POST", "/api/method/frappe.client.insert", {"doc": doc})["message"]

	def rename(self, doctype, old, new):
		return self._call("POST", "/api/method/frappe.client.rename_doc", {"doctype": doctype, "old_name": old, "new_name": new})

	def update(self, doctype, name, values):
		return self._call("PUT", f"/api/resource/{urllib.parse.quote(doctype)}/{urllib.parse.quote(name)}", values)["data"]


# ----------------------------------------------------------------------------- workbook helpers


def sheet(path, name, key):
	ws = openpyxl.load_workbook(path, data_only=True)[name]
	rows = list(ws.iter_rows(values_only=True))
	hi = next(i for i, r in enumerate(rows) if key in [str(x).strip() if x else "" for x in r])
	header = [str(x).strip() if x else "" for x in rows[hi]]
	return [dict(zip(header, r)) for r in rows[hi + 1 :] if any(x not in (None, "") for x in r)]


def txt(v):
	if v is None:
		return ""
	if isinstance(v, float) and v.is_integer():
		v = int(v)
	s = re.sub(r"\s+", " ", str(v)).strip()
	return "" if s in ("0", "None", "NA", "N/A", "-") else s


def digits(v):
	return re.sub(r"\D", "", txt(v))


def date(v):
	if isinstance(v, datetime.datetime):
		return v.date().isoformat()
	if isinstance(v, datetime.date):
		return v.isoformat()
	s = txt(v)
	for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"):
		try:
			return datetime.datetime.strptime(s, fmt).date().isoformat()
		except ValueError:
			pass
	return ""


def email(v):
	e = txt(v).lower().replace(" ", "")
	return e if re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", e) else ""


def yes(v):
	return 1 if txt(v).lower() in ("yes", "y", "1", "true") else 0


def mobile(v):
	d = digits(v)
	return d[-10:] if len(d) >= 10 else d


# ----------------------------------------------------------------------------- build the target state


def load(src):
	wf = os.path.join(src, "Work Force - HR - Master Data New.xlsx")
	master = [r for r in sheet(wf, "Master", "Emp ID") if txt(r.get("Employee Name"))]
	dataset = [r for r in sheet(wf, "Data Set", "Designation") if txt(r.get("Designation"))]
	payroll = {txt(r["Emp ID"]): r for r in sheet(os.path.join(src, "Payroll Master.xlsx"), "Payroll Master", "Emp ID") if txt(r.get("Emp ID"))}
	st = os.path.join(src, "Statutory Tracker.xlsx")
	esic = {txt(r["Emp ID"]): r for r in sheet(st, "ESIC", "Emp ID") if txt(r.get("Emp ID"))}
	epfo = {txt(r["Emp ID"]): r for r in sheet(st, "EPFO", "Emp ID") if txt(r.get("Emp ID"))}
	lwf = {txt(r["Emp ID"]): r for r in sheet(st, "LWF", "Emp ID") if txt(r.get("Emp ID"))}
	return master, dataset, payroll, esic, epfo, lwf


def build(src):
	master, dataset, payroll, esic, epfo, lwf = load(src)
	designations = {txt(r["Designation"]).lower(): r for r in dataset}
	problems = []

	def dept_name(d):
		d = txt(d)
		return f"{DEPARTMENT_MAP.get(d.lower(), d)} - {COMPANY_ABBR}" if d else ""

	def branch_name(b):
		b = txt(b)
		return BRANCH_MAP.get(b.lower(), b)

	def grade_name(g):
		g = txt(g)
		return "" if not g else (g[:-1] + g[-1].upper() if g.lower().startswith("grade ") else g)

	employees = {}
	for r in master:
		eid = txt(r.get("New ID"))
		if not eid:
			continue
		p, e, f, l = payroll.get(eid, {}), esic.get(eid, {}), epfo.get(eid, {}), lwf.get(eid, {})
		des = designations.get(txt(r.get("Designation")).lower())
		status = txt(r.get("Employment Status")) or txt(p.get("Employment Status")) or "Active"
		left = status.lower() != "active"
		address = ", ".join(x for x in (txt(r.get("Address")), txt(r.get("Street")), txt(r.get("City")), txt(r.get("District")), txt(r.get("PinCode"))) if x)
		blood = txt(r.get("Blood Group")).upper().replace(" ", "").replace("VE", "")
		emp = {
			"first_name": txt(r.get("Employee Name")),
			"employee_number": eid,
			"gender": txt(r.get("Gender")).title(),
			"date_of_birth": date(r.get("DOB")),
			"date_of_joining": date(r.get("DOJ")),
			"status": "Left" if left else "Active",
			"relieving_date": date(r.get("LWD")) or date(r.get("DOR")) or date(p.get("DOR/LWD")) if left else "",
			"reason_for_leaving": status if left else "",
			"department": dept_name(r.get("Department")),
			"designation": txt(des["Designation"]) if des else txt(r.get("Designation")),
			"branch": branch_name(r.get("Branch")),
			"grade": grade_name(r.get("Grade")) if txt(r.get("Grade")).upper() != "NA" else "",
			"employment_type": txt(r.get("Employment Type")),
			"cell_number": mobile(r.get("Personal Mobile")),
			"emergency_phone_number": mobile(r.get("Emergancy Contact Number")),
			"personal_email": email(r.get("Personal E-Mail")),
			"current_address": address,
			"blood_group": blood if blood in BLOOD else "",
			"pan_number": "" if txt(r.get("Pan Card")).upper() in ("NIL", "NILL", "NO", "NONE") else txt(r.get("Pan Card")).upper(),
			"bank_name": txt(r.get("Bank")) or txt(p.get("Bank")),
			"bank_ac_no": digits(r.get("Account No")) or digits(p.get("Account No")),
			"ifsc_code": txt(r.get("IFSC Code") or p.get("IFSC Code")).upper(),
			"salary_mode": "Bank" if (digits(r.get("Account No")) or digits(p.get("Account No"))) else "",
			"ctc": p.get("Annual CTC") if isinstance(p.get("Annual CTC"), (int, float)) and p.get("Annual CTC") else "",
			"custom_father_name": txt(r.get("Father's Name")),
			"custom_aadhaar_number": digits(r.get("Aadhaar Number")) or digits(e.get("Aadhaar No")) or digits(f.get("Aadhaar No")),
			"custom_uan_number": digits(f.get("PF UAN No")) or digits(r.get("UAN No (PF)")),
			"custom_esic_number": digits(e.get("ESICNo")) or digits(r.get("ESI No")),
			"custom_lwf_number": digits(l.get("LWF No")),
			"custom_pf_applicable": yes(p.get("PF Applicability")),
			"custom_esi_applicable": yes(p.get("ESI Applicability")),
			"custom_lwf_applicable": yes(p.get("LWF Applicability")),
			"custom_payroll_group": txt(r.get("Payroll Group")) or txt(p.get("Payroll Group")),
			"custom_salary_band": txt(p.get("Salary Band")),
			"custom_work_location": branch_name(r.get("Work Location")),
			"custom_sub_department": txt(r.get("Function / Sub-department")),
			"custom_old_employee_code": txt(r.get("Emp ID")),
		}
		if txt(r.get("Personal E-Mail")) and not emp["personal_email"]:
			problems.append((eid, emp["first_name"], f"Email is not valid: {txt(r.get('Personal E-Mail'))}"))
		for need in ("gender", "date_of_birth", "date_of_joining"):
			if not emp[need]:
				problems.append((eid, emp["first_name"], f"Missing {need.replace('_', ' ')} (required to create the employee)"))
		if left and not emp["relieving_date"]:
			problems.append((eid, emp["first_name"], f"{status} but no LWD/DOR date"))
		if emp["ifsc_code"] and not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", emp["ifsc_code"]):
			problems.append((eid, emp["first_name"], f"IFSC looks wrong: {emp['ifsc_code']}"))
		if emp["pan_number"] and not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", emp["pan_number"]):
			problems.append((eid, emp["first_name"], f"PAN looks wrong: {emp['pan_number']}"))
		if emp["custom_aadhaar_number"] and len(emp["custom_aadhaar_number"]) != 12:
			problems.append((eid, emp["first_name"], f"Aadhaar is not 12 digits: {emp['custom_aadhaar_number']}"))
		if emp["custom_esi_applicable"] and not emp["custom_esic_number"]:
			problems.append((eid, emp["first_name"], "ESI applicable but no ESIC number"))
		if emp["custom_pf_applicable"] and not emp["custom_uan_number"]:
			problems.append((eid, emp["first_name"], "PF applicable but no UAN"))
		employees[eid] = emp

	masters = {
		"Department": sorted({e["department"] for e in employees.values() if e["department"]} | {f"{DEPARTMENT_MAP.get(txt(r['Department']).lower(), txt(r['Department']))} - {COMPANY_ABBR}" for r in dataset if txt(r.get("Department"))}),
		"Designation": sorted({txt(r["Designation"]) for r in dataset}),
		"Branch": sorted({e["branch"] for e in employees.values() if e["branch"]}),
		"Employee Grade": sorted({e["grade"] for e in employees.values() if e["grade"]}),
		"Employment Type": sorted({e["employment_type"] for e in employees.values() if e["employment_type"]}),
	}
	return employees, masters, problems


# ----------------------------------------------------------------------------- compare and apply


def same(a, b):
	if isinstance(a, (int, float)) or isinstance(b, (int, float)):
		try:
			return float(a or 0) == float(b or 0)
		except (TypeError, ValueError):
			return False
	return (txt(a) or "") == (txt(b) or "")


def plan(site, employees, masters):
	live_masters = {dt: {r["name"] for r in site.get_all(dt)} for dt in masters}
	create_masters = [(dt, n) for dt, names in masters.items() for n in names if n not in live_masters[dt]]
	live_cf = {r["fieldname"] for r in site.get_all("Custom Field", ["fieldname"], [["dt", "=", "Employee"]])}
	create_cf = [f for f in CUSTOM_FIELDS if f["fieldname"] not in live_cf]
	have_cf = live_cf | {f["fieldname"] for f in CUSTOM_FIELDS}

	fields = ["name"] + sorted({k for e in employees.values() for k in e if not k.startswith("custom_") or k in live_cf})
	live = {r["name"]: r for r in site.get_all("Employee", fields)}
	# Created earlier under a naming-series name but not yet renamed to the FTR/CST ID.
	by_number = {r["employee_number"]: r for r in live.values() if r.get("employee_number") and r["employee_number"] != r["name"]}
	updates, creates, checks, skipped, renames = [], [], [], [], []
	for eid, target in sorted(employees.items()):
		target = {k: v for k, v in target.items() if k in have_cf or not k.startswith("custom_")}
		if eid not in live and eid in by_number:
			renames.append((by_number[eid]["name"], eid))
			live[eid] = by_number[eid]
		if eid in live:
			cur = live[eid]
			diff = {k: v for k, v in target.items() if v not in ("", None) and not same(cur.get(k), v)}
			for k in KEEP_IF_SET:
				if k in diff and cur.get(k):
					checks.append((eid, cur.get("first_name"), k, txt(cur.get(k)), txt(diff.pop(k))))
			if diff:
				updates.append((eid, diff, {k: cur.get(k) for k in diff}))
		else:
			missing = [k.replace("_", " ") for k in REQUIRED if not target.get(k)]
			if target.get("status") == "Left" and not target.get("relieving_date"):
				missing.append("relieving date (left)")
			dob, doj = target.get("date_of_birth"), target.get("date_of_joining")
			if dob and (dob > datetime.date.today().isoformat() or (doj and dob >= doj)):
				missing.append(f"a valid date of birth ({dob})")
			if missing:
				skipped.append((eid, target.get("first_name"), ", ".join(missing)))
				continue
			creates.append((eid, {k: v for k, v in target.items() if v not in ("", None)}))
	extra = sorted(set(live) - set(employees) - {old for old, _ in renames})
	return create_masters, create_cf, updates, creates, extra, checks, skipped, renames


def report(path, create_masters, create_cf, updates, creates, extra, checks, skipped, renames, problems, employees):
	wb = openpyxl.Workbook()
	ws = wb.active
	ws.title = "Summary"
	for row in [
		("Masters to create", len(create_masters)),
		("Employee custom fields to add", len(create_cf)),
		("Employees to update", len(updates)),
		("Employees to create", len(creates)),
		("Employees to rename to their ID", len(renames)),
		("On the site but not in the workbook (left as they are)", len(extra)),
		("Name / date of birth differs: kept as on the site, HR to check", len(checks)),
		("Not created: required details missing", len(skipped)),
		("Problems to fix in the workbook", len(problems)),
	]:
		ws.append(row)
	ws = wb.create_sheet("Masters")
	ws.append(("DocType", "Name"))
	for r in create_masters:
		ws.append(r)
	ws = wb.create_sheet("Custom Fields")
	ws.append(("Field", "Label", "Type"))
	for f in create_cf:
		ws.append((f["fieldname"], f.get("label"), f["fieldtype"]))
	ws = wb.create_sheet("Updates")
	ws.append(("Employee", "Name", "Field", "Now", "New"))
	for eid, diff, cur in updates:
		for k, v in diff.items():
			ws.append((eid, employees[eid]["first_name"], k, txt(cur.get(k)), txt(v)))
	ws = wb.create_sheet("New Employees")
	cols = sorted({k for _, d in creates for k in d})
	ws.append(["Employee"] + cols)
	for eid, d in creates:
		ws.append([eid] + [txt(d.get(c)) for c in cols])
	ws = wb.create_sheet("Not In Workbook")
	ws.append(("Employee",))
	for e in extra:
		ws.append((e,))
	ws = wb.create_sheet("HR to Check")
	ws.append(("Employee", "Name on site", "Field", "On the site (kept)", "In the workbook"))
	for c in checks:
		ws.append(c)
	ws = wb.create_sheet("Not Created")
	ws.append(("Employee", "Name", "Missing"))
	for c in skipped:
		ws.append(c)
	ws = wb.create_sheet("Problems")
	ws.append(("Employee", "Name", "Problem"))
	for p in problems:
		ws.append(p)
	for s in wb.worksheets:
		for col in s.columns:
			s.column_dimensions[col[0].column_letter].width = min(60, max(10, *(len(txt(c.value)) + 2 for c in col)))
	wb.save(path)


def apply(site, create_masters, create_cf, updates, creates, renames, company):
	done, failed = collections.Counter(), []

	def attempt(label, fn):
		try:
			fn()
			done[label] += 1
		except RuntimeError as e:
			failed.append((label, str(e)))

	for dt, name in create_masters:
		doc = {"doctype": dt}
		doc.update(
			{
				"Department": {"department_name": name.rsplit(f" - {COMPANY_ABBR}", 1)[0], "company": company, "parent_department": "All Departments"},
				"Designation": {"designation_name": name},
				"Branch": {"branch": name},
				"Employee Grade": {"__newname": name},
				"Employment Type": {"employee_type_name": name},
			}[dt]
		)
		attempt(dt, lambda doc=doc: site.insert(doc))
	for f in create_cf:
		attempt("Custom Field", lambda f=f: site.insert({"doctype": "Custom Field", "dt": "Employee", **f}))
	for old, eid in renames:
		attempt("Employee renamed", lambda old=old, eid=eid: site.rename("Employee", old, eid))
	for eid, diff, _ in updates:
		attempt("Employee updated", lambda eid=eid, diff=diff: site.update("Employee", eid, diff))
	for eid, d in creates:
		attempt(
			"Employee created",
			lambda eid=eid, d=d: create_employee(site, eid, d, company),
		)
	return done, failed


def create_employee(site, eid, values, company):
	"""Employee names come from the naming series; rename to the FTR/CST ID right after."""
	doc = site.insert({"doctype": "Employee", "naming_series": "HR-EMP-", "company": company, **values})
	if doc["name"] != eid:
		site.rename("Employee", doc["name"], eid)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--dir", default=os.path.expanduser("~/Downloads"))
	ap.add_argument("--report", default="HR Sync - dry run.xlsx")
	ap.add_argument("--apply", action="store_true")
	a = ap.parse_args()
	url, token = os.environ.get("FUTURE_URL"), os.environ.get("FUTURE_TOKEN")
	if not url or not token:
		sys.exit("Set FUTURE_URL and FUTURE_TOKEN (key:secret) in the environment.")
	site = Site(url, token)
	employees, masters, problems = build(a.dir)
	company = site.get_all("Company")[0]["name"]
	result = plan(site, employees, masters)
	report(a.report, *result, problems, employees)
	create_masters, create_cf, updates, creates, extra, checks, skipped, renames = result
	print(f"masters to create: {len(create_masters)}, custom fields: {len(create_cf)}, employees to update: {len(updates)}, to create: {len(creates)}, to rename: {len(renames)}, not created: {len(skipped)}, HR to check: {len(checks)}, not in workbook: {len(extra)}, problems: {len(problems)}")
	print(f"report: {os.path.abspath(a.report)}")
	if a.apply:
		done, failed = apply(site, *result[:4], renames, company)
		print("applied:", dict(done))
		for label, err in failed:
			print("FAILED", label, err[:300])


if __name__ == "__main__":
	main()
