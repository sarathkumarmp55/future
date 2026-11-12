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
		remove_broken_workspace_links,
		unblock_future_module_for_sales_users,
	)

	for patch in (
		copy_lead_source_to_utm_source,
		backfill_lead_assignment,
		unblock_future_module_for_sales_users,
		remove_broken_workspace_links,
		course_category_master,
	):
		patch.execute()
	frappe.db.commit()


def after_migrate():
	# Workspaces are synced on every migrate; drop links to DocTypes/Reports/Pages that do not exist
	# (e.g. "Timetable Generator" left behind by an app that was removed).
	from future.patches.remove_broken_workspace_links import execute
	from future.setup import education_home

	execute()
	education_home.ensure()
