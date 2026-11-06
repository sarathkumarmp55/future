from frappe.model.document import Document
from frappe.utils import cint


class Hostel(Document):
	def validate(self):
		self.total_capacity = cint(self.ac_capacity) + cint(self.non_ac_capacity)
