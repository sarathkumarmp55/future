"""Attendance cycle shared by payroll and consultant fees.

HR counts attendance for a month from the 24th of the previous month to the 23rd: the last days
of the month are not known when payroll is prepared, so they are taken as present and any
absence in them is deducted in the next month.
"""

import frappe
from frappe.utils import add_days, add_months, cint, get_first_day, get_last_day, getdate


def hr_setting(field, default=None):
	"""Future HR Settings value; a field never saved yet returns `default` (a Single reads it as 0)."""
	saved = frappe.db.sql("select value from `tabSingles` where doctype = 'Future HR Settings' and field = %s", field)
	if not saved or saved[0][0] in (None, ""):
		return default
	return saved[0][0]


def attendance_cycle(month_date):
	"""(from_date, to_date) whose attendance decides the pay of the month containing `month_date`."""
	first = getdate(get_first_day(month_date))
	cutoff = cint(hr_setting("attendance_cutoff_day", 23))
	if cutoff <= 0 or cutoff >= 28:
		return first, getdate(get_last_day(first))
	end = first.replace(day=cutoff)
	start = add_days(add_months(end, -1), 1)
	return getdate(start), end
