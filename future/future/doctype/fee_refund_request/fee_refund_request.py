"""Fee Refund Request: Requested -> Approved (manager) -> Paid (submit; posts the refund
Payment Entry). Paid refunds reduce the enrollment's paid amount for that category."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from future.admissions import get_available, refresh_enrollment

APPROVER_ROLES = {"System Manager", "Sales Manager", "Accounts Manager"}


def is_approver(user=None):
	return bool(APPROVER_ROLES & set(frappe.get_roles(user or frappe.session.user)))


class FeeRefundRequest(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Refund amount must be more than zero."))
		if self.docstatus == 0:
			self.available = get_available(self.enrollment, self.category)
			if flt(self.amount) > flt(self.available):
				frappe.throw(
					_("Only {0} has been paid towards {1}; the refund cannot be more than that.").format(
						frappe.format_value(self.available, {"fieldtype": "Currency"}), _(self.category)
					)
				)
		if self.is_new():
			self.status = "Requested"

	def before_submit(self):
		if self.status != "Approved":
			frappe.throw(_("A manager has to approve the refund before it is paid."))
		if not (self.mode_of_payment and self.paid_from):
			frappe.throw(_("Enter the mode of payment and the account the refund is paid from."))
		self.payment_entry = self.make_payment_entry()
		self.status = "Paid"

	def on_submit(self):
		refresh_enrollment(self.enrollment)

	def on_cancel(self):
		if self.payment_entry and frappe.db.get_value("Payment Entry", self.payment_entry, "docstatus") == 1:
			frappe.get_doc("Payment Entry", self.payment_entry).cancel()
		self.db_set("status", "Cancelled")
		refresh_enrollment(self.enrollment)

	def make_payment_entry(self):
		from erpnext.accounts.party import get_party_account

		customer = frappe.db.get_value("Student", self.student, "customer")
		if not customer:
			frappe.throw(_("Student {0} has no customer account to refund.").format(self.student))
		company = frappe.db.get_value("Account", self.paid_from, "company")
		pe = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"payment_type": "Pay",
				"party_type": "Customer",
				"party": customer,
				"company": company,
				"posting_date": self.reference_date or nowdate(),
				"mode_of_payment": self.mode_of_payment,
				"paid_from": self.paid_from,
				"paid_to": get_party_account("Customer", customer, company),
				"paid_amount": flt(self.amount),
				"received_amount": flt(self.amount),
				"reference_no": self.reference_no or self.name,
				"reference_date": self.reference_date or nowdate(),
				"remarks": _("Refund {0} ({1}) for {2}: {3}").format(self.name, self.category, self.student_name, self.reason),
			}
		)
		pe.flags.ignore_permissions = True
		pe.insert()
		pe.submit()
		return pe.name


def _load_for_decision(name):
	if not is_approver():
		frappe.throw(_("Only managers can approve or reject refunds."), frappe.PermissionError)
	doc = frappe.get_doc("Fee Refund Request", name)
	if doc.docstatus != 0 or doc.status != "Requested":
		frappe.throw(_("Only requested refunds can be approved or rejected."))
	return doc


@frappe.whitelist()
def approve(name):
	doc = _load_for_decision(name)
	doc.status = "Approved"
	doc.approved_by = frappe.session.user
	doc.save()
	doc.add_comment("Info", _("Approved by {0}").format(frappe.utils.get_fullname()))
	return doc.status


@frappe.whitelist()
def reject(name, reason):
	doc = _load_for_decision(name)
	doc.status = "Rejected"
	doc.reject_reason = reason
	doc.save()
	doc.add_comment("Info", _("Rejected by {0}: {1}").format(frappe.utils.get_fullname(), frappe.utils.escape_html(reason)))
	return doc.status
