"""Hostel allotment on Program Enrollment: allot, transfer, vacate, and occupancy.

Every action writes a Hostel Log row on the enrollment, checks the target
hostel's capacity for that room type, and keeps the hostel fee schedule honest:
paid rows are never touched; unpaid rows after a vacate are dropped; unpaid
rows after a transfer are re-priced for the new room type.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from future.admissions import build_hostel_schedule, hostel_rate, refresh_enrollment

ROOM_TYPES = ("AC", "Non AC")


# ----------------------------------------------------------------------------- occupancy


def occupancy(hostel, exclude=None):
	"""{"AC": n, "Non AC": n} of students currently allotted to `hostel`."""
	rows = frappe.db.sql(
		"""select custom_hostel_type as room_type, count(*) as n from `tabProgram Enrollment`
		where docstatus = 1 and custom_hostel = %s and custom_hostel_status = 'Allotted'
		and custom_hosteller = 'Hosteller' and name != %s
		group by custom_hostel_type""",
		(hostel, exclude or ""),
		as_dict=True,
	)
	out = dict.fromkeys(ROOM_TYPES, 0)
	for r in rows:
		out[r.room_type or "Non AC"] = out.get(r.room_type or "Non AC", 0) + r.n
	return out


def update_hostel_occupancy(hostel):
	if not hostel or not frappe.db.exists("Hostel", hostel):
		return
	occ = occupancy(hostel)
	ac_cap, non_ac_cap = frappe.db.get_value("Hostel", hostel, ["ac_capacity", "non_ac_capacity"])
	total = occ["AC"] + occ["Non AC"]
	frappe.db.set_value(
		"Hostel",
		hostel,
		{
			"ac_occupied": occ["AC"],
			"non_ac_occupied": occ["Non AC"],
			"occupied": total,
			"free_beds": max(cint(ac_cap) + cint(non_ac_cap) - total, 0),
		},
		update_modified=False,
	)


def check_capacity(hostel, room_type, exclude=None):
	status, ac_cap, non_ac_cap, name = frappe.db.get_value(
		"Hostel", hostel, ["status", "ac_capacity", "non_ac_capacity", "hostel_name"]
	)
	if status and status != "Active":
		frappe.throw(_("{0} is {1}; students cannot be allotted there.").format(name or hostel, _(status)))
	capacity = cint(ac_cap if room_type == "AC" else non_ac_cap)
	if not capacity:
		frappe.throw(_("{0} has no {1} beds.").format(name or hostel, _(room_type)))
	used = occupancy(hostel, exclude)[room_type]
	if used >= capacity:
		frappe.throw(
			_("{0} is full for {1}: {2} of {3} beds taken.").format(name or hostel, _(room_type), used, capacity),
			title=_("Hostel Full"),
		)
	return capacity - used


# ----------------------------------------------------------------------------- actions


def _load(name):
	doc = frappe.get_doc("Program Enrollment", name)
	doc.check_permission("write")
	if doc.docstatus != 1:
		frappe.throw(_("Submit the enrollment first."))
	return doc


def _log(doc, log_type, hostel, room_type, date, notes=None):
	doc.append(
		"custom_hostel_log",
		{
			"hostel": hostel,
			"log_type": log_type,
			"room_type": room_type,
			"log_date": date,
			"notes": notes,
			"logged_by": frappe.session.user,
		},
	)


def _save(doc, hostels):
	doc.flags.ignore_validate_update_after_submit = True
	doc.save()
	refresh_enrollment(doc.name)
	for h in set(filter(None, hostels)):
		update_hostel_occupancy(h)


def _unpaid_after(rows, date):
	return [r for r in rows if r.due_date and getdate(r.due_date) >= getdate(date) and not (r.paid_amount or 0)]


@frappe.whitelist()
def allot(name, hostel, room_type, date=None, notes=None):
	doc = _load(name)
	if room_type not in ROOM_TYPES:
		frappe.throw(_("Room type must be AC or Non AC."))
	if doc.custom_hostel_status == "Allotted" and doc.custom_hostel:
		frappe.throw(_("Already allotted to {0}. Use Transfer instead.").format(doc.custom_hostel))
	date = date or nowdate()
	check_capacity(hostel, room_type, exclude=doc.name)
	doc.update(
		{
			"custom_hosteller": "Hosteller",
			"custom_hostel": hostel,
			"custom_hostel_type": room_type,
			"custom_hostel_status": "Allotted",
			"custom_hostel_joining_date": doc.custom_hostel_joining_date or date,
		}
	)
	# keep paid / past rows (an earlier stay), replace anything unpaid from `date` on
	drop = {r.name for r in _unpaid_after(doc.custom_hostel_schedule or [], date)}
	keep = [r for r in doc.custom_hostel_schedule or [] if r.name not in drop]
	doc.set("custom_hostel_schedule", keep)
	for row in build_hostel_schedule(doc.program, room_type, date):
		doc.append("custom_hostel_schedule", row)
	_log(doc, "Allotted", hostel, room_type, date, notes)
	_save(doc, [hostel])
	return doc.name


@frappe.whitelist()
def transfer(name, hostel, room_type, date=None, notes=None):
	doc = _load(name)
	if doc.custom_hostel_status != "Allotted" or not doc.custom_hostel:
		frappe.throw(_("The student is not in a hostel. Use Allot instead."))
	if hostel == doc.custom_hostel and room_type == doc.custom_hostel_type:
		frappe.throw(_("That is the current hostel and room type."))
	date = date or nowdate()
	check_capacity(hostel, room_type, exclude=doc.name)
	old_hostel = doc.custom_hostel

	if room_type != doc.custom_hostel_type:
		new_rate = hostel_rate(doc.program, room_type)
		for row in _unpaid_after(doc.custom_hostel_schedule or [], date):
			row.amount = new_rate

	doc.update({"custom_hostel": hostel, "custom_hostel_type": room_type})
	_log(doc, "Transferred", hostel, room_type, date, notes or _("From {0}").format(old_hostel))
	_save(doc, [old_hostel, hostel])
	return doc.name


@frappe.whitelist()
def vacate(name, date=None, notes=None):
	doc = _load(name)
	if doc.custom_hostel_status != "Allotted":
		frappe.throw(_("The student is not in a hostel."))
	date = date or nowdate()
	drop = {r.name for r in _unpaid_after(doc.custom_hostel_schedule or [], date)}
	doc.set("custom_hostel_schedule", [r for r in doc.custom_hostel_schedule if r.name not in drop])
	hostel = doc.custom_hostel
	doc.custom_hostel_status = "Vacated"
	_log(doc, "Vacated", hostel, doc.custom_hostel_type, date, notes)
	_save(doc, [hostel])
	return {"removed_rows": len(drop)}


@frappe.whitelist()
def get_hostel_options(room_type=None, location=None):
	"""Active hostels with free beds, for the allot / transfer dialogs."""
	filters = {"status": "Active"}
	if location:
		filters["location"] = location
	out = []
	for h in frappe.get_all(
		"Hostel",
		filters=filters,
		fields=["name", "hostel_name", "location", "ac_capacity", "non_ac_capacity"],
		order_by="hostel_name asc",
	):
		occ = occupancy(h.name)
		free_ac = cint(h.ac_capacity) - occ["AC"]
		free_non_ac = cint(h.non_ac_capacity) - occ["Non AC"]
		free = free_ac if room_type == "AC" else free_non_ac if room_type == "Non AC" else free_ac + free_non_ac
		out.append(
			{
				"value": h.name,
				"label": f"{h.hostel_name or h.name} · {h.location or ''}",
				"description": _("{0} AC / {1} Non AC beds free").format(max(free_ac, 0), max(free_non_ac, 0)),
				"free": free,
			}
		)
	return out


# ----------------------------------------------------------------------------- hooks


def on_enrollment_change(doc, method=None):
	"""Keep hostel occupancy right when an enrollment is submitted, cancelled or edited."""
	hostels = {doc.custom_hostel}
	before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	if before:
		hostels.add(before.get("custom_hostel"))
	for h in hostels:
		update_hostel_occupancy(h)


def refresh_all_occupancy():
	"""Daily safety net."""
	for h in frappe.get_all("Hostel", pluck="name"):
		update_hostel_occupancy(h)
