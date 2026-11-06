"""Fee Transfer Request: move paid money between fee categories of one student (Self)
or to another student's enrollment (posts a Journal Entry between their accounts).
Only managers can submit (approve) it."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from future.admissions import get_available, refresh_enrollment


class FeeTransferRequest(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be more than zero."))
		if self.transfer_type == "Self":
			self.to_enrollment = None
			if self.from_category == self.to_category:
				frappe.throw(_("Choose a different category to move the money to."))
		else:
			if not self.to_enrollment or self.to_enrollment == self.from_enrollment:
				frappe.throw(_("Choose the other student's enrollment."))
		if self.docstatus == 0:
			self.available = get_available(self.from_enrollment, self.from_category)
			if flt(self.amount) > flt(self.available):
				frappe.throw(
					_("Only {0} is available in {1}.").format(
						frappe.format_value(self.available, {"fieldtype": "Currency"}), _(self.from_category)
					)
				)

	def before_submit(self):
		self.approved_by = frappe.session.user
		if self.transfer_type == "Student to Student":
			self.journal_entry = self.make_journal_entry()

	def on_submit(self):
		self.refresh_enrollments()
		self.add_comment("Info", _("Approved by {0}").format(frappe.utils.get_fullname()))

	def on_cancel(self):
		if self.journal_entry and frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus") == 1:
			frappe.get_doc("Journal Entry", self.journal_entry).cancel()
		self.refresh_enrollments()

	def refresh_enrollments(self):
		refresh_enrollment(self.from_enrollment)
		if self.to_enrollment:
			refresh_enrollment(self.to_enrollment)

	def make_journal_entry(self):
		from erpnext.accounts.party import get_party_account

		def customer_of(enrollment):
			student = frappe.db.get_value("Program Enrollment", enrollment, "student")
			customer = frappe.db.get_value("Student", student, "customer")
			if not customer:
				frappe.throw(_("Student {0} has no customer account.").format(student))
			return customer

		src, dst = customer_of(self.from_enrollment), customer_of(self.to_enrollment)
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
		amount = flt(self.amount)
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": company,
				"posting_date": nowdate(),
				"user_remark": _("Fee transfer {0}: {1} -> {2}. {3}").format(
					self.name, self.from_student_name, self.to_student_name, self.reason
				),
				"accounts": [
					{"account": get_party_account("Customer", src, company), "party_type": "Customer", "party": src, "debit_in_account_currency": amount},
					{"account": get_party_account("Customer", dst, company), "party_type": "Customer", "party": dst, "credit_in_account_currency": amount},
				],
			}
		)
		je.flags.ignore_permissions = True
		je.insert()
		je.submit()
		return je.name
