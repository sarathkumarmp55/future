"""Salary Slip for Future: attendance is read for the attendance cycle (see cycle.py) and
Professional Tax is trued up at the end of each half-year (see professional_tax.py)."""

import frappe
from frappe.query_builder.functions import Count
from frappe.utils import add_days, getdate
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip

from future.hr import professional_tax as pt
from future.hr.cycle import attendance_cycle


class FutureSalarySlip(SalarySlip):
	def eval_condition_and_formula(self, struct_row, data):
		amount = super().eval_condition_and_formula(struct_row, data)
		# Only the actual deduction (prorated context) on our structures; the full-month default keeps the formula.
		if (
			struct_row.salary_component == pt.COMPONENT
			and struct_row.formula
			and data is getattr(self, "data", None)
			and self.payroll_frequency == "Monthly"
			and (self.salary_structure or "").startswith("Future ")
		):
			amount = pt.professional_tax(self, data.get("base"), data.get("gross_pay")) or None
			if amount:
				data[struct_row.abbr] = amount
		return amount

	def _cycle(self):
		"""Cycle for a monthly slip, kept inside the employee's joining and relieving dates."""
		if self.payroll_frequency != "Monthly" or not self.end_date:
			return None
		start, end = attendance_cycle(self.end_date)
		if getdate(self.start_date) <= start and getdate(self.end_date) >= end and start.month == end.month:
			return None  # no cut-off set: calendar month, standard behaviour
		if self.get("actual_end_date") and getdate(self.actual_end_date) < getdate(self.end_date):
			end = getdate(self.end_date)  # last month of service: count up to the last working day
		return start, end

	def get_employee_attendance(self, start_date, end_date):
		cycle = self._cycle()
		if not cycle:
			return super().get_employee_attendance(start_date, end_date)
		rows = super().get_employee_attendance(*cycle)
		# The standard code skips absences on holidays of the slip period only; do the same for
		# the days of the previous month that belong to this cycle.
		before = add_days(getdate(self.start_date), -1)
		if cycle[0] <= before and not self._count_holiday_attendance():
			holidays = set(self.get_holidays_for_employee(cycle[0], before))
			rows = [
				r
				for r in rows
				if not (getdate(r.attendance_date) in holidays and r.status in ("Absent", "Half Day"))
			]
		return rows

	def get_half_absent_days(self, consider_marked_attendance_on_holidays, holidays):
		cycle = self._cycle()
		if not cycle:
			return super().get_half_absent_days(consider_marked_attendance_on_holidays, holidays)
		Attendance = frappe.qb.DocType("Attendance")
		query = (
			frappe.qb.from_(Attendance)
			.select(Count("*"))
			.where(
				(Attendance.attendance_date.between(cycle[0], cycle[1]))
				& (Attendance.employee == self.employee)
				& (Attendance.docstatus == 1)
				& (Attendance.status == "Half Day")
				& (Attendance.half_day_status == "Absent")
			)
		)
		if not consider_marked_attendance_on_holidays:
			before = add_days(getdate(self.start_date), -1)
			all_holidays = list(holidays or [])
			if cycle[0] <= before:
				all_holidays += self.get_holidays_for_employee(cycle[0], before)
			if all_holidays:
				query = query.where(Attendance.attendance_date.notin(all_holidays))
		return query.run()[0][0]

	def _count_holiday_attendance(self):
		s = frappe.get_cached_value(
			"Payroll Settings", None, ("include_holidays_in_total_working_days", "consider_marked_attendance_on_holidays"), as_dict=1
		)
		return bool(s.include_holidays_in_total_working_days and s.consider_marked_attendance_on_holidays)
