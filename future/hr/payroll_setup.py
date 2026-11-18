"""Payroll setup for Future (rules confirmed by HR on 2026-11-17).

Staff
  Basic            51% of gross, at least 15,100 (never more than gross)
  HRA              40% of Basic, or what is left of gross if that is less
  Other Allowance  the rest of gross
  PF               12% of earned Basic, at most 3,000 (employee and employer), if PF applies
  ESI              0.75% employee + 3.25% employer of earned gross, if ESI applies and gross <= 21,000
  LWF              50 employee + 50 employer, if LWF applies (Kerala)
  Professional Tax Kerala half-yearly slab on six months of gross, spread over the six months
Apprentice (incl. management trainees)
  Stipend          fixed, no deductions
Consultants are paid through Purchase (see consultant fees), not payroll.

`setup()` creates accounts, salary components and the two salary structures; `assign()` gives each
active Staff / Apprentice employee a Salary Structure Assignment from Employee.custom_monthly_gross.
Both are safe to run again: existing records are left alone.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

PAYROLL_START = "2026-04-01"
MIN_BASIC = 15100
STAFF, APPRENTICE = "Future Staff", "Future Apprentice"

# Kerala Professional Tax, half-yearly income slab -> half-yearly tax, collected as one sixth a month.
PT_SLABS = ((125000, 1250), (100000, 1000), (45000, 750), (30000, 600), (18000, 450), (12000, 320))


def _pt_formula():
	parts = [f"{-(-tax // 6)} if base * 6 >= {limit}" for limit, tax in PT_SLABS]
	return " else ".join(parts) + " else 0"


COMPONENTS = [
	# name, abbr, type, account key, extra
	("Basic", "B", "Earning", "salary", {"depends_on_payment_days": 1}),
	("House Rent Allowance", "HRA", "Earning", "salary", {"depends_on_payment_days": 1}),
	("Other Allowance", "OA", "Earning", "salary", {"depends_on_payment_days": 1}),
	("Stipend", "STP", "Earning", "stipend", {"depends_on_payment_days": 1}),
	("Provident Fund", "PF", "Deduction", "pf", {}),
	("Employee State Insurance", "ESI", "Deduction", "esi", {}),
	("Labour Welfare Fund", "LWF", "Deduction", "lwf", {}),
	("Professional Tax", "PT", "Deduction", "pt", {}),
	("Employer Provident Fund", "PFER", "Employer Contribution", "pf_er", {}),
	("Employer ESI", "ESIER", "Employer Contribution", "esi_er", {}),
	("Employer Labour Welfare Fund", "LWFER", "Employer Contribution", "lwf_er", {}),
]

# HRMS does not let one payment-days component use another in its formula (it would be reduced
# twice), so HRA and Other Allowance are written from `base` (monthly gross) alone.
_BASIC = f"min(base, max(round(base * 0.51), {MIN_BASIC}))"
_HRA = f"min(round(({_BASIC}) * 0.4), base - ({_BASIC}))"
_OTHER = f"base - ({_BASIC}) - ({_HRA})"

STRUCTURES = {
	STAFF: {
		"earnings": [
			("Basic", None, _BASIC),
			("House Rent Allowance", f"({_HRA}) > 0", _HRA),
			("Other Allowance", f"({_OTHER}) > 0", _OTHER),
		],
		"deductions": [
			("Provident Fund", "custom_pf_applicable == 1", "min(round(B * 0.12), 3000)"),
			("Employee State Insurance", "custom_esi_applicable == 1 and base <= 21000", "ceil(gross_pay * 0.0075)"),
			("Labour Welfare Fund", "custom_lwf_applicable == 1", "50"),
			("Professional Tax", "base * 6 >= 12000", _pt_formula()),
		],
		"employer_contributions": [
			("Employer Provident Fund", "custom_pf_applicable == 1", "min(round(B * 0.12), 3000)"),
			("Employer ESI", "custom_esi_applicable == 1 and base <= 21000", "ceil(gross_pay * 0.0325)"),
			("Employer Labour Welfare Fund", "custom_lwf_applicable == 1", "50"),
		],
	},
	APPRENTICE: {"earnings": [("Stipend", None, "base")], "deductions": [], "employer_contributions": []},
}
GROUP_STRUCTURE = {"Staff": STAFF, "Apprentice": APPRENTICE}


# ----------------------------------------------------------------------------- accounts


def _company():
	return frappe.defaults.get_global_default("company") or frappe.get_all("Company", pluck="name")[0]


def _group(company, root_type, names):
	for name in names:
		acc = frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 1}, "name")
		if acc:
			return acc
	return frappe.db.get_value(
		"Account", {"company": company, "root_type": root_type, "is_group": 1, "parent_account": ["is", "set"]}, "name"
	)


def _account(company, account_name, root_type, parents, log, account_type=None):
	acc = frappe.db.get_value("Account", {"company": company, "account_name": account_name, "is_group": 0}, "name")
	if acc:
		return acc
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"company": company,
			"account_name": account_name,
			"parent_account": _group(company, root_type, parents),
			"root_type": root_type,
			"account_type": account_type,
		}
	).insert(ignore_permissions=True)
	log.append(f"Account created: {doc.name}")
	return doc.name


def ensure_accounts(company, log):
	expense = ("Indirect Expenses", "Expenses")
	liability = ("Duties and Taxes", "Current Liabilities")
	salary = frappe.db.get_value("Account", {"company": company, "account_name": "Salary", "is_group": 0}, "name")
	return {
		"salary": salary or _account(company, "Salary", "Expense", expense, log),
		"stipend": _account(company, "Stipend", "Expense", expense, log),
		"pf": _account(company, "Provident Fund Payable", "Liability", liability, log),
		"esi": _account(company, "ESI Payable", "Liability", liability, log),
		"lwf": _account(company, "Labour Welfare Fund Payable", "Liability", liability, log),
		"pt": _account(company, "Professional Tax Payable", "Liability", liability, log),
		"pf_er": _account(company, "Employer PF Contribution", "Expense", expense, log),
		"esi_er": _account(company, "Employer ESI Contribution", "Expense", expense, log),
		"lwf_er": _account(company, "Employer LWF Contribution", "Expense", expense, log),
	}


# ----------------------------------------------------------------------------- components and structures


def ensure_components(company, accounts, log):
	liability_for = {"pf_er": "pf", "esi_er": "esi", "lwf_er": "lwf"}
	for name, abbr, ctype, key, extra in COMPONENTS:
		if frappe.db.exists("Salary Component", name):
			doc = frappe.get_doc("Salary Component", name)
		else:
			doc = frappe.get_doc(
				{"doctype": "Salary Component", "salary_component": name, "salary_component_abbr": abbr, "type": ctype, **extra}
			)
			log.append(f"Salary Component created: {name}")
		# ERPNext's default "Provident Fund" / "Professional Tax" are reduced by payment days; ours are
		# worked out from earned Basic or fixed, and the structure takes this flag from the component.
		doc.depends_on_payment_days = extra.get("depends_on_payment_days", 0)
		if not any(a.company == company for a in doc.get("accounts")):
			row = {"company": company, "account": accounts[key]}
			if key in liability_for:
				row["liability_account"] = accounts[liability_for[key]]
			doc.append("accounts", row)
		doc.flags.ignore_permissions = True
		doc.save()


def ensure_structures(company, log):
	abbr = {name: frappe.db.get_value("Salary Component", name, "salary_component_abbr") for name, *_ in COMPONENTS}
	# Rows carry their own payment-days flag: components that existed before (ERPNext's defaults)
	# may be set differently, and deductions written from earned Basic must not be reduced again.
	by_days = {name: extra.get("depends_on_payment_days", 0) for name, _a, _t, _k, extra in COMPONENTS}
	for name, tables in STRUCTURES.items():
		if frappe.db.exists("Salary Structure", name):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Salary Structure",
				"__newname": name,
				"company": company,
				"is_active": "Yes",
				"payroll_frequency": "Monthly",
				"currency": frappe.get_cached_value("Company", company, "default_currency"),
			}
		)
		for table, rows in tables.items():
			for component, condition, formula in rows:
				doc.append(
					table,
					{
						"salary_component": component,
						"abbr": abbr[component],
						"condition": condition,
						"amount_based_on_formula": 1,
						"formula": formula.replace("B * 0.12", f"{abbr['Basic']} * 0.12"),
						"depends_on_payment_days": by_days[component],
					},
				)
		doc.insert(ignore_permissions=True)
		doc.submit()
		log.append(f"Salary Structure created: {name}")


@frappe.whitelist()
def setup():
	frappe.only_for("System Manager")
	log = []
	company = _company()
	accounts = ensure_accounts(company, log)
	ensure_components(company, accounts, log)
	ensure_structures(company, log)
	return log


# ----------------------------------------------------------------------------- assignments


@frappe.whitelist()
def assign(dry_run=1):
	"""Give each active Staff / Apprentice employee their structure with base = monthly gross.

	An employee whose gross changed since the last assignment gets a new assignment from today."""
	frappe.only_for("System Manager")
	dry_run = frappe.utils.cint(dry_run)
	company = _company()
	log, skipped = [], []
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "custom_payroll_group": ["in", list(GROUP_STRUCTURE)]},
		fields=["name", "employee_name", "custom_payroll_group", "custom_monthly_gross", "date_of_joining"],
		order_by="name",
	)
	for e in employees:
		gross = flt(e.custom_monthly_gross)
		if not gross:
			skipped.append(f"{e.name} {e.employee_name}: no monthly gross")
			continue
		structure = GROUP_STRUCTURE[e.custom_payroll_group]
		current = frappe.get_all(
			"Salary Structure Assignment",
			filters={"employee": e.name, "docstatus": 1},
			fields=["name", "base", "salary_structure", "from_date"],
			order_by="from_date desc",
			limit=1,
		)
		if current and flt(current[0].base) == gross and current[0].salary_structure == structure:
			continue
		from_date = (
			frappe.utils.today() if current else max(getdate(e.date_of_joining), getdate(PAYROLL_START)).isoformat()
		)
		log.append(f"{e.name} {e.employee_name}: {structure}, {gross:,.0f} from {from_date}")
		if dry_run:
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Salary Structure Assignment",
				"employee": e.name,
				"salary_structure": structure,
				"company": company,
				"from_date": from_date,
				"base": gross,
				"currency": frappe.get_cached_value("Company", company, "default_currency"),
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
	return {"dry_run": dry_run, "assigned": len(log), "skipped": skipped, "log": log}


# ----------------------------------------------------------------------------- consultants (Purchase)

FEE_ITEM = "Professional Fee"
SUPPLIER_GROUP = "Consultants"


@frappe.whitelist()
def setup_consultants(dry_run=1):
	"""Fee item, supplier group, TDS category in Future HR Settings, and a Supplier per consultant.

	Suppliers are linked on Employee.custom_supplier; consultants that already have one are skipped."""
	frappe.only_for("System Manager")
	dry_run = frappe.utils.cint(dry_run)
	company = _company()
	log = []

	tds = frappe.db.get_value("Tax Withholding Category", {"name": ["like", "%194J%"]}, "name")
	if not tds:
		log.append("No Tax Withholding Category for Section 194J found: set it in Future HR Settings.")

	if not dry_run:
		if not frappe.db.exists("Supplier Group", SUPPLIER_GROUP):
			frappe.get_doc({"doctype": "Supplier Group", "supplier_group_name": SUPPLIER_GROUP}).insert(ignore_permissions=True)
		if not frappe.db.exists("Item", FEE_ITEM):
			expense = _account(company, "Professional Fees", "Expense", ("Indirect Expenses", "Expenses"), log)
			item = frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": FEE_ITEM,
					"item_name": FEE_ITEM,
					"item_group": frappe.db.get_value("Item Group", {"is_group": 0, "name": "Services"}, "name")
					or frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
					"stock_uom": "Nos",
					"is_stock_item": 0,
					"is_purchase_item": 1,
					"is_sales_item": 0,
					"gst_hsn_code": frappe.db.get_value("GST HSN Code", {"name": ["like", "9983%"]}, "name")
					or frappe.db.get_value("GST HSN Code", {"name": ["like", "99%"]}, "name"),
					"item_defaults": [{"company": company, "expense_account": expense}],
				}
			)
			item.insert(ignore_permissions=True)
			log.append(f"Item created: {FEE_ITEM}")
		settings = frappe.get_single("Future HR Settings")
		settings.consultant_fee_item = settings.consultant_fee_item or FEE_ITEM
		settings.consultant_supplier_group = settings.consultant_supplier_group or SUPPLIER_GROUP
		settings.consultant_tds_category = settings.consultant_tds_category or tds
		settings.attendance_cutoff_day = settings.attendance_cutoff_day or 23
		settings.consultant_leaves_per_month = settings.consultant_leaves_per_month or 4
		settings.save(ignore_permissions=True)

	for e in frappe.get_all(
		"Employee",
		filters={"custom_payroll_group": "Consultant", "status": "Active", "custom_supplier": ["is", "not set"]},
		fields=["name", "employee_name", "pan_number"],
		order_by="name",
	):
		supplier_name = e.employee_name
		if frappe.db.exists("Supplier", supplier_name):
			supplier_name = f"{e.employee_name} ({e.name})"
		log.append(f"Supplier for {e.name}: {supplier_name}")
		if dry_run:
			continue
		supplier = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": supplier_name,
				"supplier_group": SUPPLIER_GROUP,
				"supplier_type": "Individual",
				"pan": e.pan_number,
				"tax_withholding_category": tds,
			}
		)
		supplier.insert(ignore_permissions=True)
		frappe.db.set_value("Employee", e.name, "custom_supplier", supplier.name, update_modified=False)
	return {"dry_run": dry_run, "log": log}
