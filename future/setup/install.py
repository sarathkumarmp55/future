"""Install-time setup.

Frappe marks an app's patches as already run when the app is installed (they are meant for
upgrading existing data), so the data steps below are called here too: a site that installs
Future on top of existing leads and workspaces gets them done straight away."""

import frappe


def after_install():
	from future.patches import (
		backfill_lead_assignment,
		copy_lead_source_to_utm_source,
		course_category_master,
		lead_board_and_categories,
		remove_broken_workspace_links,
		unblock_future_module_for_sales_users,
	)

	for patch in (
		copy_lead_source_to_utm_source,
		backfill_lead_assignment,
		unblock_future_module_for_sales_users,
		remove_broken_workspace_links,
		course_category_master,
		lead_board_and_categories,
	):
		patch.execute()
	frappe.db.commit()


def after_migrate():
	# Workspaces are synced on every migrate; drop links to DocTypes/Reports/Pages that do not exist
	# (e.g. "Timetable Generator" left behind by an app that was removed).
	from future.patches.lead_board_and_categories import copy_lead_categories
	from future.patches.remove_broken_workspace_links import execute
	from future.setup import education_home

	execute()
	education_home.ensure()
	copy_lead_categories()
	ensure_roles()


def ensure_roles():
	"""Roles the app's permission rules refer to (see future.permissions.visibility)."""
	if not frappe.db.exists("Role", "Lead Uploader"):
		frappe.get_doc({"doctype": "Role", "role_name": "Lead Uploader", "desk_access": 1}).insert(ignore_permissions=True)
