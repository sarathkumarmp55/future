# Copyright (c) 2026, sarath and contributors
# For license information, please see license.txt

# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
from frappe.utils import flt
# pyrefly: ignore [missing-import]
from frappe.model.document import Document


class PaymentApprovalLog(Document):
	def on_submit(self):
		if self.payment_status == "Approved":
			try:
				student = frappe.get_doc({
					"doctype": "Student",
					"first_name": self.student_name,
					"custom_age": self.age,
					"custom_payment_approval_log":self.name,
					"student_name": self.student_name,
					"student_email_id": self.email_id
				})
				# Skip Student's validate_user() hook — it tries to create a Frappe User
				# which fails when no valid system email is present
				student.flags.ignore_validate = True
				student.flags.ignore_mandatory = True
				student.insert(ignore_permissions=True)

				# Save the generated Student ID back into this log
				frappe.db.set_value("Payment Approval Log", self.name, "student", student.name)
				# frappe.db.commit()

				# Create and submit Program Enrollment for the new student
				enrollment = frappe.get_doc({
					"doctype": "Program Enrollment",
					"student": student.name,
					"program": self.program,
					"custom_payment_approvallog":self.name,
					"academic_year": self.academic_year
				})
				enrollment.flags.ignore_permissions = True
				enrollment.flags.ignore_mandatory = True
				enrollment.insert(ignore_permissions=True)
				enrollment.submit()

				# Fetch Fee Structure and copy its components into Fees
				fee_structure_doc = frappe.get_doc("Fee Structure", self.fee_structure)
				grand_total = fee_structure_doc.total_amount

				# Create and submit Fees for the new student
				fees = frappe.get_doc({
					"doctype": "Fees",
					"student": student.name,
					"program_enrollment": enrollment.name,
					"fee_structure": self.fee_structure,
					"due_date": "2027-07-21",
					"academic_year": self.academic_year,
					"custom_payment_approval_log": self.name,
					"receivable_account": fee_structure_doc.receivable_account,
					"income_account": fee_structure_doc.income_account,
					"cost_center": fee_structure_doc.cost_center
				})

				# Loop through Fee Structure components and append to Fees
				for component in fee_structure_doc.components:
					fees.append("components", {
						"fees_category": component.fees_category,
						"amount": component.amount
					})
					# grand_total += flt(component.amount)

				fees.grand_total = grand_total
				fees.flags.ignore_permissions = True
				fees.flags.ignore_mandatory = True
				fees.insert(ignore_permissions=True)
				fees.submit()

				payment_entry = frappe.get_doc({
					"doctype": "Payment Entry",
					"payment_type": "Receive",
					"party_type": "Student",
					"party": student.name,
					"posting_date": self.date,
					"mode_of_payment": self.mode_of_payment,
					"paid_amount": flt(self.received_amount),
					"received_amount": flt(self.received_amount),
					"base_received_amount": flt(self.received_amount),
					"source_exchange_rate": 1,
					"target_exchange_rate": 1,
					"company": self.company,
					"custom_payment_approval_log": self.name,
					"cost_center": fee_structure_doc.cost_center,
					"paid_from": fee_structure_doc.receivable_account,
					"paid_to" : self.account_paid_to,
					"paid_to_account_currency": "INR",
					"paid_from_account_currency": "INR",
				})

				payment_entry.append("references", {
					"reference_doctype": "Fees",
					"reference_name": fees.name,
					"total_amount": flt(fees.grand_total),
					"allocated_amount": flt(self.received_amount),
					# "outstanding_amount": flt(self.balance)
				})




				payment_entry.flags.ignore_permissions = True
				payment_entry.flags.ignore_mandatory = True
				payment_entry.insert(ignore_permissions=True)
				payment_entry.submit()

				frappe.msgprint(
					f" Payment of <b>{self.received_amount}</b> received from <b>{self.student_name}</b> has been successfully allocated.",
					title="Records Created",
					indicator="green"
				)

			except Exception as e:
				# Re-raise as frappe.throw so the entire submit transaction rolls back
						frappe.log_error(
						message=frappe.get_traceback(),
						title="Payment Approval Log"
					)
