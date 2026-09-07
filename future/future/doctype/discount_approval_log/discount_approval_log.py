# Copyright (c) 2026, sarath and contributors
# For license information, please see license.txt

# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
from frappe.utils import flt
# pyrefly: ignore [missing-import]
from frappe.model.document import Document


class DiscountApprovalLog(Document):
	def on_submit(self):
		if self.discount_status != "Approved":
			return

		if not self.opportunity_reference:
			frappe.throw("Cannot submit because Opportunity Reference is not set")

		opportunity = frappe.get_doc("Opportunity", self.opportunity_reference)

		if opportunity.custom_discount_approved:
			frappe.throw("Discount has already been applied to this Opportunity")

		if not opportunity.custom_fees_details:
			frappe.throw("Cannot submit because the custom_fees_details table has no rows")

		if len(opportunity.custom_fees_details) > 1:
			frappe.throw(
				"Cannot submit because the custom_fees_details table has more than 1 row value"
			)

		discount = flt(self.amount)
		if discount <= 0:
			frappe.throw("Cannot submit because Discount Amount must be greater than 0")

		row = opportunity.custom_fees_details[0]
		if discount > flt(row.amount) or discount > flt(opportunity.custom_program_total_amount):
			frappe.throw("Cannot submit because Discount Amount exceeds the fee amount")

		new_amount = flt(row.amount) - discount
		new_total = flt(opportunity.custom_program_total_amount) - discount

		child_doctype = frappe.get_meta("Opportunity").get_field("custom_fees_details").options

		frappe.db.set_value(child_doctype, row.name, "amount", new_amount)
		frappe.db.set_value(
			"Opportunity",
			self.opportunity_reference,
			"custom_program_total_amount",
			new_total,
		)
		frappe.db.set_value(
			"Opportunity",
			self.opportunity_reference,
			"status",
			"Discount Approved",
		)
		frappe.db.set_value(
			"Lead",
			self.lead_reference,
			"status",
			"Discount Approved",
		)
		frappe.db.set_value(
			"Opportunity",
			self.opportunity_reference,
			"custom_discount_approved",
			1,
		)
