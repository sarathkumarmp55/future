"""Kerala Professional Tax, the way HR works it out (PT 1st Half FY 26-27 workings, Nov 2026).

The tax is a half-yearly amount set by the half-year's earnings (April-September, October-March).
For the first four months one sixth of the amount for the expected earnings (monthly gross x 6)
is deducted. In the last two months the amount is worked out again from what was actually earned
and the balance is collected: half in the fifth month, the rest in the sixth.

  1,250 slab: 208 x 4, then 209 + 209.
"""

import frappe
from frappe.utils import add_months, flt, get_first_day, getdate

# half-yearly earnings from -> half-yearly tax
PT_SLABS = ((125000, 1250), (100000, 1000), (45000, 750), (30000, 600), (18000, 450), (12000, 320))
COMPONENT = "Professional Tax"


def half_year_tax(earnings):
	for limit, tax in PT_SLABS:
		if flt(earnings) >= limit:
			return tax
	return 0


def monthly_share(tax):
	return int(tax / 6 + 0.5)


def half_year_start(date):
	date = getdate(date)
	first = 4 if 4 <= date.month <= 9 else 10
	year = date.year if date.month >= first or first == 4 else date.year - 1
	return getdate(f"{year}-{first:02d}-01")


def professional_tax(slip, base, gross_pay):
	"""Professional Tax for a monthly salary slip. `base` is the monthly gross, `gross_pay` what
	was earned this month."""
	base, gross_pay = flt(base), flt(gross_pay)
	start = half_year_start(slip.start_date)
	this_month = get_first_day(slip.start_date)
	month_no = (this_month.year - start.year) * 12 + this_month.month - start.month + 1
	usual = monthly_share(half_year_tax(base * 6))
	if month_no <= 4:
		return usual

	earned, deducted, months = _so_far(slip, start, this_month)
	# Months paid outside the system (before payroll moved here) are taken as normal months.
	first_month = max(start, get_first_day(_joining(slip.employee) or start))
	missing = (this_month.year - first_month.year) * 12 + this_month.month - first_month.month - months
	if missing > 0:
		earned += missing * base
		deducted += missing * usual

	if month_no == 5:
		balance = half_year_tax(earned + gross_pay + base) - deducted
		return max(int(balance / 2 + 0.5), 0)
	return max(half_year_tax(earned + gross_pay) - deducted, 0)


def _joining(employee):
	return frappe.get_cached_value("Employee", employee, "date_of_joining")


def _so_far(slip, start, this_month):
	"""Gross earned and Professional Tax deducted on this half-year's earlier salary slips."""
	slips = frappe.get_all(
		"Salary Slip",
		filters={
			"employee": slip.employee,
			"docstatus": ["<", 2],
			"start_date": ["between", [start, add_months(this_month, -1)]],
			"name": ["!=", slip.name or ""],
		},
		fields=["name", "gross_pay", "start_date"],
	)
	if not slips:
		return 0, 0, 0
	deducted = frappe.get_all(
		"Salary Detail",
		filters={"parent": ["in", [s.name for s in slips]], "parentfield": "deductions", "salary_component": COMPONENT},
		pluck="amount",
	)
	months = len({get_first_day(s.start_date) for s in slips})
	return sum(flt(s.gross_pay) for s in slips), sum(flt(a) for a in deducted), months
