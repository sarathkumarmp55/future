import frappe


def execute():
	"""Salespeople had the `future` module blocked, which hides the Leads rail and
	dashboard sidebar. Lead privacy is enforced per record, so unblocking is safe."""
	sales_users = frappe.db.sql_list(
		"""select distinct r.parent from `tabHas Role` r
		where r.role in ('Sales User', 'Sales Manager') and r.parenttype = 'User'"""
	)
	if not sales_users:
		return
	frappe.db.delete(
		"Block Module",
		{"parenttype": "User", "module": "future", "parent": ["in", sales_users]},
	)
	frappe.clear_cache()
