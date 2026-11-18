"""Monthly professional fee for consultants, paid through Purchase.

Rule (HR, 2026-11-17): a consultant has a number of paid days off each month (4), unused days
carry forward; days off beyond that are unpaid and reduce the monthly fee by days. Example: in a
30-day month, 25 days worked = 5 days off, 4 are paid, 1 unpaid: fee for 29 days.

Attendance is read for the attendance cycle (Future HR Settings: cut-off day), like payroll.
Submitting creates one draft Purchase Invoice per consultant for accounts to check (GST, TDS)
and submit.
"""

import calendar

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_first_day, get_last_day, getdate

from future.hr.cycle import attendance_cycle, hr_setting

WORKED = {"Present": 1, "Work From Home": 1, "Half Day": 0.5}


class ConsultantFeeRun(Document):
	def validate(self):
		self.fee_month = get_first_day(self.fee_month)
		self.title = getdate(self.fee_month).strftime("%B %Y")
		self.from_date, self.to_date = attendance_cycle(self.fee_month)
		self.days_in_month = calendar.monthrange(getdate(self.fee_month).year, getdate(self.fee_month).month)[1]
		if not self.items:
			self.get_consultants()
		self.calculate()

	@frappe.whitelist()
	def get_consultants(self):
		"""List every active consultant with a monthly fee and read their attendance."""
		self.validate_dates()
		self.set("items", [])
		for e in frappe.get_all(
			"Employee",
			filters={"custom_payroll_group": "Consultant", "date_of_joining": ["<=", get_last_day(self.fee_month)]},
			or_filters={"status": "Active", "relieving_date": [">=", self.fee_month]},
			fields=["name", "custom_monthly_gross", "custom_supplier"],
			order_by="name",
		):
			if not flt(e.custom_monthly_gross):
				continue
			worked, marked = self.worked_days(e.name)
			cycle_days = (getdate(self.to_date) - getdate(self.from_date)).days + 1
			self.append(
				"items",
				{
					"employee": e.name,
					"supplier": e.custom_supplier,
					"monthly_fee": e.custom_monthly_gross,
					"worked_days": worked if marked else cycle_days,
					"off_days": cycle_days - worked if marked else 0,
					"leave_opening": self.carried_in(e.name),
					"remarks": "" if marked else _("No attendance marked in this period: paid in full, please check."),
				},
			)
		self.calculate()

	def validate_dates(self):
		self.fee_month = get_first_day(self.fee_month)
		self.from_date, self.to_date = attendance_cycle(self.fee_month)
		self.days_in_month = calendar.monthrange(getdate(self.fee_month).year, getdate(self.fee_month).month)[1]

	def worked_days(self, employee):
		rows = frappe.get_all(
			"Attendance",
			filters={"employee": employee, "docstatus": 1, "attendance_date": ["between", [self.from_date, self.to_date]]},
			fields=["status"],
		)
		return sum(WORKED.get(r.status, 0) for r in rows), bool(rows)

	def carried_in(self, employee):
		"""Paid days off left over from the previous submitted run."""
		prev = frappe.db.sql(
			"""select i.leave_closing from `tabConsultant Fee Run Item` i
			inner join `tabConsultant Fee Run` r on r.name = i.parent
			where i.employee = %s and r.docstatus = 1 and r.fee_month < %s
			order by r.fee_month desc limit 1""",
			(employee, self.fee_month),
		)
		return flt(prev[0][0]) if prev else 0

	def calculate(self):
		per_month = flt(hr_setting("consultant_leaves_per_month", 4))
		total = 0
		for row in self.items:
			row.off_days = max(flt(row.off_days), 0)
			row.leave_allowed = flt(row.leave_opening) + per_month
			paid_off = min(row.off_days, row.leave_allowed)
			row.lwp_days = row.off_days - paid_off
			row.leave_closing = row.leave_allowed - paid_off
			row.payable_days = max(self.days_in_month - row.lwp_days, 0)
			row.amount = flt(flt(row.monthly_fee) * row.payable_days / self.days_in_month, 0)
			total += row.amount
		self.total_amount = total

	def before_submit(self):
		missing = [f"{r.employee} {r.employee_name}" for r in self.items if flt(r.amount) and not r.supplier]
		if missing:
			frappe.throw(
				_("These consultants have no Supplier yet (run 'Create Suppliers' first):<br>{0}").format("<br>".join(missing)),
				title=_("Supplier missing"),
			)

	def on_submit(self):
		item = hr_setting("consultant_fee_item")
		if not item:
			frappe.throw(_("Set the Fee Item in Future HR Settings."))
		created = 0
		for row in self.items:
			if not flt(row.amount) or row.purchase_invoice:
				continue
			pi = frappe.get_doc(
				{
					"doctype": "Purchase Invoice",
					"company": self.company,
					"supplier": row.supplier,
					"posting_date": get_last_day(self.fee_month),
					"set_posting_time": 1,
					"bill_date": get_last_day(self.fee_month),
					"remarks": _("Professional fee for {0}: {1} of {2} days ({3} unpaid). {4}").format(
						self.title, flt(row.payable_days), self.days_in_month, flt(row.lwp_days), self.name
					),
					"items": [
						{
							"item_code": item,
							"qty": 1,
							"rate": row.amount,
							"description": _("Professional fee, {0}").format(self.title),
						}
					],
				}
			)
			pi.flags.ignore_permissions = True
			pi.set_missing_values()
			pi.insert()
			row.db_set("purchase_invoice", pi.name)
			created += 1
		self.db_set("invoices_created", created)

	def on_cancel(self):
		for row in self.items:
			if not row.purchase_invoice:
				continue
			status = frappe.db.get_value("Purchase Invoice", row.purchase_invoice, "docstatus")
			if status == 1:
				frappe.throw(
					_("Purchase Invoice {0} is already submitted. Cancel it first.").format(row.purchase_invoice)
				)
			if status == 0:
				frappe.delete_doc("Purchase Invoice", row.purchase_invoice, ignore_permissions=True)
			row.db_set("purchase_invoice", None)
