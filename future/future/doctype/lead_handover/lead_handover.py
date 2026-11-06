"""Lead Handover: the logged way to move leads between salespeople.

Two ways in:
- A Team Lead / Lead Manager / Sales Manager creates and submits it: leads move.
- A salesperson saves it as a *request* (request_status = Requested) for leads
  they hold; their heads are notified and approve (submit) or reject it.

Submitting moves every lead to its `to_user` (see future.lead_management);
cancelling hands each lead back to the single person it came from.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from future.lead_management import (
	_notify,
	can_manage_leads,
	check_can_hand_over,
	colleagues_of,
	current_holders,
	hand_over_lead,
	heads_of,
)


class LeadHandover(Document):
	def validate(self):
		self.dedupe_leads()
		manager = can_manage_leads()

		if self.is_new() and not manager:
			self.request_status = "Requested"
			self.requested_by = frappe.session.user

		if self.request_status == "Requested" and not manager:
			self.validate_request()
		else:
			self.handed_over_by = frappe.session.user
			self.set_targets()
			for row in self.leads:
				check_can_hand_over(row.lead, row.to_user)

		for row in self.leads:
			row.from_users = ", ".join(current_holders(row.lead, self.role))
		self.total_leads = len(self.leads)

	def after_insert(self):
		if self.request_status == "Requested":
			_notify(
				heads_of(self.requested_by),
				_("{0} asks to hand over {1} lead(s): {2}").format(
					frappe.utils.get_fullname(self.requested_by), len(self.leads), self.reason
				),
				"Lead Handover",
				self.name,
				self.requested_by,
			)

	def dedupe_leads(self):
		seen, rows = set(), []
		for row in self.leads:
			if row.lead and row.lead not in seen:
				seen.add(row.lead)
				rows.append(row)
		if len(rows) != len(self.leads):
			self.set("leads", rows)
		if not self.leads:
			frappe.throw(_("Add at least one lead."))

	def validate_request(self):
		user = frappe.session.user
		if self.handover_type != "Hand Over" or self.role != "Lead User":
			frappe.throw(_("A request can only ask to hand over your own leads."))
		if not heads_of(user):
			frappe.throw(_("You are not in a team, so there is nobody to approve a request."))
		for row in self.leads:
			if user not in current_holders(row.lead, "Lead User"):
				frappe.throw(_("Lead {0} is not assigned to you.").format(row.lead), frappe.PermissionError)
		if self.to_user and self.to_user not in colleagues_of(user):
			frappe.throw(_("{0} is not in your team.").format(frappe.utils.get_fullname(self.to_user)))
		self.set("targets", [])
		for row in self.leads:
			row.to_user = self.to_user

	def set_targets(self):
		if self.handover_type == "Hand Over":
			if not self.to_user:
				frappe.throw(_("Choose who the leads go to."))
			self.set("targets", [])
			for row in self.leads:
				row.to_user = self.to_user
			return

		users = []
		for t in self.targets:
			if t.user and t.user not in users:
				users.append(t.user)
		if len(users) < 2:
			frappe.throw(_("Distribute needs at least two salespeople."))
		self.to_user = None
		counts = dict.fromkeys(users, 0)
		for i, row in enumerate(self.leads):
			row.to_user = users[i % len(users)]
			counts[row.to_user] += 1
		for t in self.targets:
			t.lead_count = counts.get(t.user, 0)

	def before_submit(self):
		if self.request_status == "Rejected":
			frappe.throw(_("This request was rejected."))
		if not can_manage_leads():
			frappe.throw(_("Your Team Lead has to approve this request."), frappe.PermissionError)
		if self.request_status == "Requested":
			self.request_status = "Approved"

	def on_submit(self):
		for row in self.leads:
			previous = hand_over_lead(row.lead, row.to_user, self.role, reason=self.reason, reference=self.name)
			row.db_set("from_users", ", ".join(previous))
		self.db_set("handover_on", now_datetime())
		if self.requested_by:
			_notify(
				[self.requested_by],
				_("Your hand-over request {0} was approved").format(self.name),
				"Lead Handover",
				self.name,
				frappe.session.user,
			)

	def on_cancel(self):
		for row in self.leads:
			previous = [u.strip() for u in (row.from_users or "").split(",") if u.strip()]
			if len(previous) != 1:
				continue
			check_can_hand_over(row.lead, previous[0])
			hand_over_lead(
				row.lead,
				previous[0],
				self.role,
				reason=_("Hand-over {0} was cancelled").format(self.name),
				reference=self.name,
			)
