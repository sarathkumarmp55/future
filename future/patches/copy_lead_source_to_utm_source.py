import frappe


def execute():
	"""ERPNext 16 replaced Lead.source (Link Lead Source) with Lead.utm_source (Link UTM Source).
	The old column survives in the table with the real data, so copy it across."""
	if not frappe.db.has_column("Lead", "source"):
		return

	for (value,) in frappe.db.sql(
		"select distinct source from `tabLead` where ifnull(source, '') != '' and ifnull(utm_source, '') = ''"
	):
		if not frappe.db.exists("UTM Source", value):
			frappe.get_doc({"doctype": "UTM Source", "__newname": value, "name": value}).insert(
				ignore_permissions=True, set_name=value
			)

	frappe.db.sql(
		"update `tabLead` set utm_source = source where ifnull(source, '') != '' and ifnull(utm_source, '') = ''"
	)
