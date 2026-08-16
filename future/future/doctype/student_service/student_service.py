# Copyright (c) 2026, sarath and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StudentService(Document):
	def on_submit(self):
		log = frappe.new_doc("Payment Approval Log")
		log.from_student_service = 1
		log.student_id = self.student
		log.date = frappe.utils.today()
		log.transaction_id = self.transaction_id
		log.transaction_date = self.transaction_date
		log.mode_of_payment = self.mode_of_payement
		log.attach = self.attach
		log.account_paid_to = self.account_paid_to
		log.student_service_id = self.name

		if self.fees == 1:
			log.fees = 1
			log.program = self.program
			log.fees_received_amount = self.received_amount
			log.total_amount = self.total_amount
			for row in self.fees_components:
				log.append("fee_details", {
					"components": row.components,
					"amount": row.amount,
					"received_amount": row.received_amount
				})

		if self.hostel_required == 1:
			log.hostel_required = 1
			log.hostel = self.hostel
			log.hostel_total_amount = self.hostel_total_amount
			log.hostel_received_amount = self.hostel_received_amount
			for row in self.hostel_components:
				log.append("hostel_components", {
					"components": row.components,
					"amount": row.amount,
					"received_amount": row.received_amount
				})

		if self.vehicle_required == 1:
			log.vehicle_required = 1
			log.vehicle = self.vehicle
			log.vehicle_total_amount = self.vehicle_total_amount
			log.vehicle_received_amount = self.vehicle_received_amount
			for row in self.vehicle_components:
				log.append("vehicle_components", {
					"components": row.components,
					"amount": row.amount,
					"received_amount": row.received_amount
				})	

		log.insert(ignore_permissions=True)
