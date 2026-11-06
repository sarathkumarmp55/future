"""Import the "Masters - Program&Hostel&Center.xlsx" workbook (Center, Hostel,
Program price split, price chart) into the site. Safe to run again: records are
matched and updated, never duplicated.

    bench --site <site> execute future.setup.import_masters.run --kwargs "{'path': '/path/to/Masters.xlsx'}"
"""

import re

import frappe
from frappe.utils import cint, flt, getdate

FEE_GROUP = "Fee Component"
GENERIC_ITEMS = {
	"Registration Fee": "GST 18%",
	"Material Fee": "GST 18%",
	"Orientation Fee": "GST 18%",
	# Same treatment as the existing "Hostel Fee" item; confirm with the accountant.
	"Transportation Fee": "Non-GST",
	"Tablet Fee": "Non-GST",
	"Caution Deposit": "Non-GST",
}


def _sheet(wb, name, header_word):
	ws = wb[name]
	rows = [list(r) for r in ws.iter_rows(values_only=True)]
	for i, r in enumerate(rows):
		if any(isinstance(c, str) and c.strip().lower() == header_word.lower() for c in r):
			header = [str(c).strip() if c is not None else "" for c in r]
			return header, [r for r in rows[i + 1 :] if any(c not in (None, "", " ") for c in r)]
	frappe.throw(f"Header '{header_word}' not found in sheet {name}")


def _col(header, row, *names, nth=0):
	idx = [i for i, h in enumerate(header) if h.lower() in [n.lower() for n in names]]
	if len(idx) <= nth:
		return None
	v = row[idx[nth]] if idx[nth] < len(row) else None
	return v.strip() if isinstance(v, str) else v


def _location(name, log):
	if not name:
		return None
	existing = frappe.db.sql_list("select name from `tabLocation` where lower(location_name) = lower(%s)", name.strip())
	if existing:
		return existing[0]
	doc = frappe.get_doc({"doctype": "Location", "location_name": name.strip().upper()}).insert(ignore_permissions=True)
	log.append(f"Location created: {doc.name}")
	return doc.name


def _tax_template(prefix):
	if not prefix:
		return None
	return frappe.db.get_value("Item Tax Template", {"name": ["like", f"{prefix}%"]}, "name")


def _ensure_item(code, tax_prefix=None):
	if frappe.db.exists("Item", code):
		template = _tax_template(tax_prefix)
		if template and not frappe.db.exists("Item Tax", {"parent": code, "parenttype": "Item"}):
			item = frappe.get_doc("Item", code)
			item.append("taxes", {"item_tax_template": template})
			item.save(ignore_permissions=True)
		return code
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": code,
			"item_group": FEE_GROUP,
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_sales_item": 1,
		}
	)
	if frappe.get_meta("Item").has_field("gst_hsn_code"):
		# same SAC as the existing program items (commercial training & coaching)
		item.gst_hsn_code = frappe.db.sql(
			"""select gst_hsn_code from `tabItem` where item_group = %s and ifnull(gst_hsn_code, '') != ''
			group by gst_hsn_code order by count(*) desc limit 1""",
			FEE_GROUP,
		)[0][0]
	template = _tax_template(tax_prefix)
	if template:
		item.append("taxes", {"item_tax_template": template})
	item.insert(ignore_permissions=True)
	return code


def _norm(s):
	return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _academic_year(text, start=None, end=None, log=None):
	"""'2026 - 2028' -> '2026-2027' style Academic Year (first year), created if missing."""
	m = re.findall(r"(20\d\d)", str(text or ""))
	if not m:
		return None
	first = int(m[0])
	name = f"{first}-{first + 1}"
	if not frappe.db.exists("Academic Year", name):
		frappe.get_doc(
			{
				"doctype": "Academic Year",
				"academic_year_name": name,
				"year_start_date": f"{first}-06-01",
				"year_end_date": f"{first + 1}-05-31",
			}
		).insert(ignore_permissions=True)
		log and log.append(f"Academic Year created: {name}")
	return name


def _match_program(excel_name, academic_year_text, existing):
	"""Map Excel names like 'DHRUVA NEET - 2027' / 'FUTURE INTEGRATED SCHOOL - NEET [2026-2028]' to Program names."""
	years = re.findall(r"20\d\d", str(academic_year_text or ""))
	suffix = f"{years[0]} - {years[-1]}" if years else ""
	base = re.sub(r"\s*-\s*20\d\d\s*$", "", excel_name.strip())
	fsp = re.match(r"FUTURE INTEGRATED SCHOOL\s*-\s*(NEET|JEE)\s*\[(20\d\d)-(20\d\d)\]", excel_name.strip(), re.I)
	candidates = []
	if fsp:
		stream, y1, y2 = fsp.group(1).upper(), fsp.group(2), fsp.group(3)
		level = "Plus One" if int(y2) - int(y1) == 2 else "Plus Two"
		candidates.append(f"FSP {stream} {level}-{y1} - {y2}")
	candidates.append(f"{base}-{suffix}")
	lookup = {_norm(n): n for n in existing}
	for c in candidates:
		if _norm(c) in lookup:
			return lookup[_norm(c)], candidates[0]
	return None, candidates[0]


def run(path, dry_run=0):
	import openpyxl

	wb = openpyxl.load_workbook(path, data_only=True)
	log = []

	for code, tax in GENERIC_ITEMS.items():
		_ensure_item(code, tax)

	# ---- Centers
	header, rows = _sheet(wb, "Center Master", "Location")
	for r in rows:
		name = _col(header, r, "Building Name As per Future")
		if not name:
			continue
		ctype = "School" if "school" in name.lower() else "Crash Course" if "crash" in name.lower() else "Campus"
		values = {
			"location": _location(_col(header, r, "Location"), log),
			"center_type": ctype,
			"address": _col(header, r, "Address"),
			"capacity": cint(_col(header, r, "Capacity")),
			"area_sqft": flt(_col(header, r, "Area (Sq ft)")),
		}
		if frappe.db.exists("Center", name):
			frappe.get_doc("Center", name).update(values).save(ignore_permissions=True)
		else:
			frappe.get_doc({"doctype": "Center", "center_name": name, **values}).insert(ignore_permissions=True)
			log.append(f"Center created: {name}")

	# ---- Hostels
	header, rows = _sheet(wb, "Hostel Master", "Hostel Code")
	for r in rows:
		code = _col(header, r, "Hostel Code")
		if not code:
			continue
		start = _col(header, r, "Hostel Start Date")
		status = _col(header, r, "Hostel Status") or "Active"
		if isinstance(start, str) and "yet" in start.lower():
			status, start = "Yet to Open", None
		esc = _col(header, r, "Escalation Rate")
		values = {
			"hostel_code": code,
			"hostel_name": _col(header, r, "Hostel Name As per Future") or code,
			"location": _location(_col(header, r, "Location"), log),
			"locality": _col(header, r, "Location", nth=1),
			"address": _col(header, r, "Address"),
			"status": status if status in ("Active", "Yet to Open", "Vacated") else "Active",
			"start_date": getdate(start) if start else None,
			"vacated_date": getdate(_col(header, r, "Hostel Vacated Date")) if _col(header, r, "Hostel Vacated Date") else None,
			"security_deposit": flt(_col(header, r, "Security Deposit")),
			"monthly_rent": flt(_col(header, r, "Monthly Rent")),
			"rcm_applicable": 1 if str(_col(header, r, "RCM Applicability") or "").lower() == "applicable" else 0,
			"rcm_gst": flt(_col(header, r, "RCM GST")),
			"payment_day": str(_col(header, r, "Payment Date") or "").strip(),
			"escalation_period": _col(header, r, "Escalation Period"),
			"escalation_rate": flt(esc) * 100 if esc and flt(esc) < 1 else flt(esc),
			"notice_period": _col(header, r, "Notice Period"),
			"ac_capacity": cint(_col(header, r, "Ac Capacity")),
			"non_ac_capacity": cint(_col(header, r, "Non Ac Capacity")),
			"area_sqft": flt(_col(header, r, "Area (Sq ft)")),
		}
		name = frappe.db.get_value("Hostel", {"hostel_code": code}, "name")
		if name:
			frappe.get_doc("Hostel", name).update(values).save(ignore_permissions=True)
		else:
			doc = frappe.get_doc({"doctype": "Hostel", **values})
			if frappe.db.exists("Item", "Hostel Fee"):
				doc.append("details", {"components": "Hostel Fee", "amount": 0})
			doc.insert(ignore_permissions=True)
			log.append(f"Hostel created: {code} {values['hostel_name']}")

	# ---- Programs
	header, rows = _sheet(wb, "Program Master", "Program Name")
	existing = frappe.get_all("Program", pluck="name")
	for r in rows:
		excel_name = _col(header, r, "Program Name")
		if not excel_name:
			continue
		ay_text = _col(header, r, "Academic Year")
		match, proposed = _match_program(excel_name, ay_text, existing)
		start, end = _col(header, r, "Start Date"), _col(header, r, "End Date")
		vertical, sub = _col(header, r, "Vertical"), _col(header, r, "Sub Vertical")
		stream = "NEET" if "NEET" in excel_name.upper() else "JEE" if "JEE" in excel_name.upper() else sub
		values = {
			"custom_start_date": getdate(start) if start else None,
			"custom_end_date": getdate(end) if end else None,
			"custom_selling_price": flt(_col(header, r, "Selling Price")),
			"custom_reg_fee": flt(_col(header, r, "Reg Fee")),
			"custom_material_fee": flt(_col(header, r, "Material Fee")),
			"custom_orientation_fee": flt(_col(header, r, "Orientation Fee")),
			"custom_course_fee": round(flt(_col(header, r, "Course Fee")), 2),
			"custom_total_amount": flt(_col(header, r, "Selling Price")),
		}
		if match:
			doc = frappe.get_doc("Program", match)
			if sub and doc.custom_sub_vertical and sub != doc.custom_sub_vertical:
				log.append(f"Note: Excel says {excel_name} is {sub}, site says {doc.custom_sub_vertical}; kept the site value.")
			doc.update(values).save(ignore_permissions=True)
			continue
		name = proposed
		_ensure_item(name, "GST 18%")
		doc = frappe.get_doc(
			{
				"doctype": "Program",
				"program_name": name,
				"program_abbreviation": re.sub(r"[^A-Z0-9]", "", name.upper())[:10],
				"custom_program_type": _col(header, r, "Program Type"),
				"custom_vertical": vertical,
				"custom_sub_vertical": stream,
				"custom_academic_year": _academic_year(ay_text, start, end, log),
				"custom_is_active": 1,
				**values,
			}
		)
		doc.append("custom_fees_details", {"component": name, "amount_with_gst": values["custom_selling_price"]})
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		existing.append(doc.name)
		log.append(f"Program created: {doc.name}")

	# ---- Price chart -> Admission Settings
	ws = wb["Price Chart - Others"]
	flat = [[c for c in r if c is not None] for r in ws.iter_rows(values_only=True)]
	s = frappe.get_single("Admission Settings")
	section, rates = None, {}
	transport = {}
	for r in flat:
		if not r:
			continue
		label = str(r[0]).strip()
		if label.lower().startswith("hostel fee - fsp plus two"):
			section = "FSP Plus Two"
		elif label.lower().startswith("hostel fee - others"):
			section = "Others"
		elif label.lower().startswith("transportation fee"):
			section = "transport"
		elif section in ("FSP Plus Two", "Others") and label in ("AC", "Non AC") and len(r) > 1:
			rates.setdefault(section, {})[label] = flt(r[1])
		elif label.lower().startswith("mess fee") and len(r) > 1:
			s.mess_fee_per_day, section = flt(r[1]), None
		elif label.lower().startswith("work book") and len(r) > 1:
			s.workbook_fee, section = flt(r[1]), None
		elif label.lower().startswith("study kit") and len(r) > 1:
			s.study_kit_fee, section = flt(r[1]), None
		elif label.lower().startswith("tablet fee") and len(r) > 1:
			s.tablet_fee, section = flt(r[1]), None
		elif label.lower().startswith("tab locking") and len(r) > 1:
			section = None
		elif section == "transport" and len(r) > 1 and isinstance(r[1], (int, float)):
			transport[label] = flt(r[1])
		for i, c in enumerate(r):
			if isinstance(c, str) and "plus two school fee" in c.lower() and i + 1 < len(r):
				s.fsp_plus_two_school_fee = flt(str(r[i + 1]).split("/")[0])
			if isinstance(c, str) and "plus one school fee" in c.lower() and i + 1 < len(r):
				s.fsp_plus_one_school_fee = flt(str(r[i + 1]).split("/")[0])
	s.set("hostel_rates", [])
	for applies, v in rates.items():
		s.append("hostel_rates", {"applies_to": applies, "ac_monthly": v.get("AC"), "non_ac_monthly": v.get("Non AC")})
	s.hostel_fee_item = s.hostel_fee_item or ("Hostel Fee" if frappe.db.exists("Item", "Hostel Fee") else None)
	s.transport_fee_item = s.transport_fee_item or "Transportation Fee"
	s.tablet_fee_item = s.tablet_fee_item or "Tablet Fee"
	s.caution_deposit_item = s.caution_deposit_item or "Caution Deposit"
	s.save(ignore_permissions=True)

	# transport fee per program family, e.g. "Repeaters NEET" -> offline repeater NEET programs
	for label, amount in transport.items():
		words = label.upper().split()
		for prog in frappe.get_all("Program", fields=["name", "custom_vertical", "custom_sub_vertical", "custom_program_type"]):
			if prog.custom_program_type != "Offline":
				continue
			fam = (prog.custom_vertical or "").upper()
			if words[0] == "REPEATERS" and fam == "REPEATERS" and words[1] == (prog.custom_sub_vertical or "").upper():
				frappe.db.set_value("Program", prog.name, "custom_transport_fee", amount)
			if words[0] == "FSP" and fam == "FSP" and words[1] in prog.name.upper() and " ".join(words[2:]).upper() in prog.name.upper():
				frappe.db.set_value("Program", prog.name, "custom_transport_fee", amount)

	if cint(dry_run):
		frappe.db.rollback()
		log.append("DRY RUN: rolled back")
	else:
		frappe.db.commit()
	for line in log:
		print(line)
	print(
		"Centers:", frappe.db.count("Center"), "| Hostels:", frappe.db.count("Hostel"),
		"| Programs:", frappe.db.count("Program"), "| Hostel rates:", rates, "| Transport:", transport,
	)
	return log
