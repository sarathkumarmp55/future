# Copyright (c) 2026, sarath and contributors
# For license information, please see license.txt

# pyrefly: ignore [missing-import]
import frappe
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
				frappe.db.commit()

				frappe.msgprint(
					f"Student created successfully. Student ID: <b>{student.name}</b>",
					title="Student Created",
					indicator="green"
				)

			except Exception as e:
				# Re-raise as frappe.throw so the entire submit transaction rolls back
				frappe.throw(
					f"Student creation failed. Submit aborted.<br><br><b>Error:</b> {str(e)}",
					title="Submit Failed"
				)
