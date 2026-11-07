"""Put the Future education overview at the top of the Education home page.

The Education workspace belongs to the Education app (not forked), so the overview is a
workspace custom block added on every migrate: idempotent, and it comes back if an Education
update re-syncs its workspace."""

import json

import frappe

BLOCK = "Future Education Overview"
WORKSPACE = "Education"
ROLES = ("System Manager", "Education Manager", "Academics User", "Sales Manager", "Accounts Manager", "Accounts User")
SCRIPT = """frappe.require(["/assets/future/js/future_dash.js", "/assets/future/js/education_dashboard.js"], () =>
	FutureEducation.mount(root_element)
);"""


def ensure():
	if not frappe.db.exists("Workspace", WORKSPACE) or not frappe.db.exists("DocType", "Custom HTML Block"):
		return

	if frappe.db.exists("Custom HTML Block", BLOCK):
		block = frappe.get_doc("Custom HTML Block", BLOCK)
	else:
		block = frappe.new_doc("Custom HTML Block")
		block.name = BLOCK
	block.update({"html": '<div id="future-education"></div>', "script": SCRIPT, "style": "", "private": 0})
	block.set("roles", [{"role": r} for r in ROLES if frappe.db.exists("Role", r)])
	if block.is_new():
		block.insert(ignore_permissions=True, set_name=BLOCK)
	else:
		block.save(ignore_permissions=True)

	ws = frappe.get_doc("Workspace", WORKSPACE)
	changed = False
	if not any(r.custom_block_name == BLOCK for r in ws.get("custom_blocks") or []):
		ws.append("custom_blocks", {"custom_block_name": BLOCK, "label": BLOCK})
		changed = True
	try:
		content = json.loads(ws.content or "[]")
	except ValueError:
		content = []
	if not any(b.get("type") == "custom_block" and b.get("data", {}).get("custom_block_name") == BLOCK for b in content):
		content.insert(0, {"id": "future-edu", "type": "custom_block", "data": {"custom_block_name": BLOCK, "col": 12}})
		ws.content = json.dumps(content)
		changed = True
	if changed:
		ws.flags.ignore_links = True
		ws.save(ignore_permissions=True)
