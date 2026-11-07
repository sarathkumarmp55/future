import frappe
from frappe.permissions import add_permission, update_permission_property


def execute():
	"""Lead form fixes (meeting of 2026-11-07).

	1. Everyone who fills a lead can pick Student Class and Year of Study: these were readable
	   only by Sales User / System Manager, so Sales Managers saw an empty dropdown.
	2. Gender no longer defaults to "Non-Conforming" (a leftover property setter that put that
	   value on almost every imported lead). It stays required in the Lead form (lead.js), but not
	   on the server, so imports and integrations without a gender save it blank instead of a
	   wrong value. Existing leads are not changed here.
	"""
	for doctype in ("Student Class", "Year of Study"):
		if not frappe.db.exists("DocType", doctype):
			continue
		for role in ("Sales User", "Sales Manager", "Academics User", "Accounts User"):
			if not frappe.db.exists("Role", role):
				continue
			add_permission(doctype, role, 0)
			update_permission_property(doctype, role, 0, "read", 1)

	for name in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Lead", "field_name": "gender", "property": ["in", ["default", "reqd"]]},
		pluck="name",
	):
		frappe.delete_doc("Property Setter", name, ignore_permissions=True)
	frappe.clear_cache(doctype="Lead")
