"""Clickable tile strips for list views (Lead, Opportunity).

Each tile is a set of list filters. The strip asks for counts with the list's
current filters, so a tile's number equals the rows it shows when clicked.
Counts use frappe.get_list, so record privacy (visibility.py) always applies.
"""

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

from future import lead_stages

OPPORTUNITY_STAGES = {
	"open": ("Open", "Replied"),
	"counselling": (
		"Course Counselling Completed",
		"Fee Discussion Completed",
		"Documents Pending",
		"Parent Decision Pending",
		"Student Decision Pending",
		"Admission Date Confirmed",
		"Quotation",
	),
	"approval": (
		"Scholarship Requested",
		"Discount Approval Pending",
		"Discount Approved",
		"Payment Approval Pending",
	),
	"won": ("Converted", "Converted Student"),
	"lost": ("Lost", "Closed"),
}


def _status(doctype, statuses):
	return [[doctype, "status", "in", list(statuses)]]


def _lead_tiles():
	t = lead_stages.tiles()
	hours = frappe.get_cached_doc("Lead Settings").first_call_hours or 24
	return [
		{"key": "all", "label": _("Total Leads"), "filters": [], "foot": _("matching the filters")},
		{"key": "new", "label": _("Not Called Yet"), "filters": t["new"][1], "foot": _("status still New")},
		{"key": "contacted", "label": _("Contacted"), "filters": t["contacted"][1], "foot": _("trying to reach")},
		{"key": "interested", "label": _("Interested"), "filters": t["interested"][1], "foot": _("in discussion")},
		{"key": "won", "label": _("Admissions"), "filters": t["won"][1], "foot": "{conversion}", "tone": "good"},
		{"key": "lost", "label": _("Lost"), "filters": t["lost"][1], "foot": _("disqualified or lost"), "tone": "muted"},
		{
			"key": "late",
			"label": _("Past First-call Limit"),
			"filters": t["late"][1],
			"foot": _("not called within {0}h").format(hours),
			"tone": "alert",
			"dynamic": 1,
		},
	]


def _opportunity_tiles():
	stale = str(add_days(now_datetime(), -7))
	closed = list(OPPORTUNITY_STAGES["won"] + OPPORTUNITY_STAGES["lost"])
	return [
		{"key": "all", "label": _("Total Opportunities"), "filters": [], "foot": _("matching the filters")},
		{"key": "open", "label": _("Open"), "filters": _status("Opportunity", OPPORTUNITY_STAGES["open"]), "foot": _("not yet counselled")},
		{
			"key": "counselling",
			"label": _("In Counselling"),
			"filters": _status("Opportunity", OPPORTUNITY_STAGES["counselling"]),
			"foot": _("counselling, fees, decisions"),
		},
		{
			"key": "approval",
			"label": _("Awaiting Approval"),
			"filters": _status("Opportunity", OPPORTUNITY_STAGES["approval"]),
			"foot": _("discount, scholarship, payment"),
			"tone": "warn",
		},
		{"key": "won", "label": _("Converted"), "filters": _status("Opportunity", OPPORTUNITY_STAGES["won"]), "foot": "{conversion}", "tone": "good"},
		{"key": "lost", "label": _("Lost"), "filters": _status("Opportunity", OPPORTUNITY_STAGES["lost"]), "foot": _("lost or closed"), "tone": "muted"},
		{
			"key": "stale",
			"label": _("No Activity 7+ Days"),
			"filters": [["Opportunity", "status", "not in", closed], ["Opportunity", "modified", "<", stale]],
			"foot": _("open, untouched for a week"),
			"tone": "alert",
			"dynamic": 1,
		},
	]


def _enrollment_tiles():
	PE, sub = "Program Enrollment", [["Program Enrollment", "docstatus", "=", 1]]
	return [
		{"key": "all", "label": _("Admissions"), "filters": [], "foot": _("matching the filters")},
		{"key": "pending", "label": _("Pending"), "filters": [[PE, "custom_admission_status", "=", "Pending"]], "foot": _("paid, not joined yet"), "tone": "warn"},
		{"key": "joined", "label": _("Joined"), "filters": [[PE, "custom_admission_status", "=", "Joined"]], "foot": _("attending"), "tone": "good"},
		{
			"key": "overdue",
			"label": _("Fees Overdue"),
			"filters": sub + [["Enrollment Fee Schedule", "status", "=", "Overdue"]],
			"foot": _("an instalment is past due"),
			"tone": "alert",
		},
		{"key": "balance", "label": _("Course Balance"), "filters": sub + [[PE, "custom_course_balance", ">", 0]], "foot": _("course fee not fully paid")},
		{
			"key": "hostellers",
			"label": _("Hostellers"),
			"filters": [[PE, "custom_hosteller", "=", "Hosteller"], [PE, "custom_hostel_status", "=", "Allotted"]],
			"foot": _("in a hostel now"),
		},
		{
			"key": "hostel_due",
			"label": _("Hostel Dues"),
			"filters": sub + [[PE, "custom_hostel_balance", ">", 0], [PE, "custom_hostel_status", "=", "Allotted"]],
			"foot": _("hostel fee balance"),
			"tone": "warn",
		},
		{
			"key": "dropped",
			"label": _("Dropped / Cancelled"),
			"filters": [[PE, "custom_admission_status", "in", ["Dropped", "Cancelled"]]],
			"foot": _("left the program"),
			"tone": "muted",
		},
	]


CONFIG = {"Lead": _lead_tiles, "Opportunity": _opportunity_tiles, "Program Enrollment": _enrollment_tiles}


@frappe.whitelist()
def get_tile_counts(doctype, filters=None):
	if doctype not in CONFIG:
		frappe.throw(_("No tiles for {0}").format(doctype))
	tiles = CONFIG[doctype]()
	owned = {f[1] for t in tiles for f in t["filters"]} - {"docstatus"}
	filters = frappe.parse_json(filters) if filters else []
	base = [f for f in filters if not (isinstance(f, (list, tuple)) and len(f) >= 2 and f[1] in owned)]

	counts = {}
	for t in tiles:
		f = base + t["filters"]
		if any(isinstance(x, (list, tuple)) and x[0] != doctype for x in f):
			# a child-table filter joins child rows; count each record once
			counts[t["key"]] = len(frappe.get_list(doctype, filters=f, pluck="name", distinct=True, limit_page_length=0))
		else:
			res = frappe.get_list(doctype, filters=f, fields=[{"COUNT": "*", "as": "n"}], order_by=None)
			counts[t["key"]] = res[0].n if res else 0
	conversion = round(counts.get("won", 0) * 100.0 / counts["all"], 1) if counts.get("all") else 0
	for t in tiles:
		t["foot"] = t["foot"].replace("{conversion}", _("{0}% conversion").format(conversion))
		t["count"] = counts[t["key"]]
		if t.get("tone") == "alert" and not t["count"]:
			t["tone"] = "muted"
	return {"tiles": tiles, "owned_fields": sorted(owned)}
