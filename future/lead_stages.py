"""Lead stages and the clickable tiles shown on the Lead list and Lead Dashboard.

One definition for both places, so a tile's number always equals the rows the
list shows when that tile is clicked. Counts go through frappe.get_list, so
lead privacy (future.permissions.visibility) applies automatically.
"""

import frappe
from frappe.utils import add_to_date, cint, now_datetime

# Lead.status values per stage. "New" is every status not listed here.
STAGES = {
	"Contacted": ("Contacted", "Did Not Pick", "Set Reminder", "Schedule Callback", "Follow-up"),
	"Interested": (
		"Interested",
		"Demo Scheduled",
		"Negotiation",
		"Opportunity",
		"Qualified",
		"Manager Approval",
		"Discount Approval Pending",
		"Discount Approved",
		"Payment Approval Pending",
	),
	"Won": ("Payment Done", "Won", "Converted Student"),
	"Lost": ("Disqualified", "Invalid", "Close Lead", "Lost"),
}


def all_statuses():
	options = frappe.get_meta("Lead").get_field("status").options or ""
	return [s for s in options.split("\n") if s.strip()]


def stage_statuses(stage):
	if stage == "New":
		taken = {s for group in STAGES.values() for s in group}
		return [s for s in all_statuses() if s not in taken]
	return list(STAGES[stage])


def stage_of(status):
	for stage, statuses in STAGES.items():
		if status in statuses:
			return stage
	return "New"


def late_filters():
	"""List filters for leads past the first-call limit (see Lead Settings)."""
	s = frappe.get_cached_doc("Lead Settings")
	untouched = [x.strip() for x in (s.untouched_statuses or "Lead\nNew").split("\n") if x.strip()]
	cutoff = add_to_date(now_datetime(), hours=-cint(s.first_call_hours or 24))
	return [
		["Lead", "status", "in", untouched],
		["Lead", "custom_lead_user", "is", "set"],
		["Lead", "custom_assigned_on", "<", str(cutoff)],
	]


def tiles():
	"""Tile key -> (label, list filters it applies)."""
	return {
		"all": ("Total Leads", []),
		"new": ("Not Called Yet", [["Lead", "status", "in", stage_statuses("New")]]),
		"contacted": ("Contacted", [["Lead", "status", "in", stage_statuses("Contacted")]]),
		"interested": ("Interested", [["Lead", "status", "in", stage_statuses("Interested")]]),
		"won": ("Admissions", [["Lead", "status", "in", stage_statuses("Won")]]),
		"lost": ("Lost", [["Lead", "status", "in", stage_statuses("Lost")]]),
		"late": ("Past First-call Limit", late_filters()),
	}


def ready_for_opportunity(lead):
	"""A lead moves to an Opportunity only once the call connected and the student is interested
	(or it is already further along the pipeline)."""
	return lead.get("custom_connected_status") == "Interested" or stage_of(lead.get("status")) in ("Interested", "Won")


@frappe.whitelist()
def can_make_opportunity(lead):
	doc = frappe.get_doc("Lead", lead)
	doc.check_permission("read")
	return ready_for_opportunity(doc)


def validate_opportunity_from_lead(doc, method=None):
	"""Opportunity before_insert: block opportunities from leads that are not interested yet."""
	if doc.opportunity_from != "Lead" or not doc.party_name or frappe.flags.in_import or frappe.flags.in_migrate:
		return
	lead = frappe.db.get_value("Lead", doc.party_name, ["status", "custom_connected_status"], as_dict=True)
	if lead and not ready_for_opportunity(lead):
		frappe.throw(
			frappe._("Create the opportunity once the lead is Connected and Interested. Update the call status on the lead first."),
			title=frappe._("Lead not interested yet"),
		)
