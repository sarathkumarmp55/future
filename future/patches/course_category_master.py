import frappe

DEFAULTS = ("School Tuition", "Higher Secondary", "NEET & JEE Programs", "Integrated School Program")


def execute():
	"""Course Categories became a DocType (Lead.custom_course_categories is now a Link).

	Creates the four categories the old dropdown offered, plus any other value already saved on
	a lead, so every existing lead still points at a real record. Categories that already exist
	are left alone."""
	frappe.reload_doc("future", "doctype", "course_category")
	used = frappe.db.sql_list(
		"select distinct custom_course_categories from `tabLead` where ifnull(custom_course_categories, '') != ''"
	) if frappe.db.has_column("Lead", "custom_course_categories") else []
	for name in (*DEFAULTS, *used):
		name = (name or "").strip()
		if name and not frappe.db.exists("Course Category", name):
			frappe.get_doc({"doctype": "Course Category", "category_name": name}).insert(ignore_permissions=True)
