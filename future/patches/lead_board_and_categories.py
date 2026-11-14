import frappe

BOARDS = ("CBSE", "State", "ICSE")
# The old per-course "Categories" dropdowns on Lead and the course category each belonged to.
OLD_FIELDS = {
	"custom_categories": "School Tuition",
	"custom_categories_2": "Higher Secondary",
	"custom_categories_3": "NEET & JEE Programs",
	"custom_categories_4": "Integrated School Program",
}
SUB_CATEGORIES = {
	"School Tuition": ("Grade 7 Tuition", "Grade 8 Tuition", "Grade 9 Tuition", "Grade 10 Tuition"),
	"Higher Secondary": ("Grade 11 Tuition + Entrance Coaching", "Grade 12 Tuition + Entrance Coaching"),
	"NEET & JEE Programs": (
		"Online NEET Repeater",
		"Online JEE Repeater",
		"One-Year Offline NEET Repeater",
		"One-Year Offline JEE Repeater",
	),
	"Integrated School Program": ("Integrated School – Grade 11", "Integrated School – Grade 12"),
}


def _used(field):
	if not frappe.db.has_column("Lead", field):
		return []
	return frappe.db.sql_list(f"select distinct `{field}` from `tabLead` where ifnull(`{field}`, '') != ''")


def execute():
	"""Board and the Lead's "Categories" became DocTypes (Board, Course Sub Category).

	Creates the old dropdown values plus any value already saved on a lead, then copies each
	lead's category from the four per-course dropdowns into the single Categories link (when the
	field exists; otherwise after_migrate does it). The old fields stay (hidden) with their data.
	Records that already exist are left alone."""
	from future.patches import course_category_master

	course_category_master.execute()
	frappe.reload_doc("future", "doctype", "board")
	frappe.reload_doc("future", "doctype", "course_sub_category")

	for name in (*BOARDS, *_used("custom_board")):
		name = name.strip()
		if name and not frappe.db.exists("Board", name):
			frappe.get_doc({"doctype": "Board", "board_name": name}).insert(ignore_permissions=True)

	wanted = [(c, s) for c, subs in SUB_CATEGORIES.items() for s in subs]
	wanted += [(c, s) for field, c in OLD_FIELDS.items() for s in _used(field)]
	for course, sub in wanted:
		sub = sub.strip()
		if sub and not frappe.db.exists("Course Sub Category", sub):
			frappe.get_doc(
				{"doctype": "Course Sub Category", "sub_category_name": sub, "course_category": course}
			).insert(ignore_permissions=True)

	copy_lead_categories()


def copy_lead_categories():
	"""Fill Lead.custom_course_sub_category from the old per-course dropdowns, once per lead.

	Called from after_migrate (the new Lead field only exists after customizations are synced,
	which happens after patches). Touches only leads whose new field is still empty."""
	if not frappe.db.has_column("Lead", "custom_course_sub_category"):
		return
	fields = [f for f in OLD_FIELDS if frappe.db.has_column("Lead", f)]
	if not fields:
		return
	pending = " or ".join(f"ifnull(`{f}`, '') != ''" for f in fields)
	if not frappe.db.sql(
		f"select 1 from `tabLead` where ifnull(custom_course_sub_category, '') = '' and ({pending}) limit 1"
	):
		return
	# Take the dropdown that matches the lead's course category first, then any filled one.
	for field in fields:
		frappe.db.sql(
			f"""update `tabLead` set custom_course_sub_category = `{field}`
			where ifnull(custom_course_sub_category, '') = '' and ifnull(`{field}`, '') != ''
			and custom_course_categories = %s""",
			OLD_FIELDS[field],
		)
	for field in fields:
		frappe.db.sql(
			f"""update `tabLead` set custom_course_sub_category = `{field}`
			where ifnull(custom_course_sub_category, '') = '' and ifnull(`{field}`, '') != ''"""
		)
