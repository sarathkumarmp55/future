import json

import frappe


def execute():
	"""Drop workspace links / shortcuts / cards that point at DocTypes, Reports or Pages
	that no longer exist (e.g. "Timetable Generator" from an app removed before v16),
	which otherwise make the workspace open with a "DocType ... not found" error."""
	for name in frappe.get_all("Workspace", pluck="name"):
		ws = frappe.get_doc("Workspace", name)
		changed = False

		def exists(link_type, target):
			if link_type in ("DocType", "Report", "Page", "Dashboard") and target:
				return bool(frappe.db.exists(link_type, target))
			return True

		links = [l for l in ws.links if l.type == "Card Break" or exists(l.link_type, l.link_to)]
		if len(links) != len(ws.links):
			ws.set("links", links)
			changed = True

		shortcuts = [s for s in ws.shortcuts if exists(s.type, s.link_to)]
		removed = {s.label for s in ws.shortcuts} - {s.label for s in shortcuts}
		if removed:
			ws.set("shortcuts", shortcuts)
			try:
				blocks = json.loads(ws.content or "[]")
				ws.content = json.dumps(
					[b for b in blocks if not (b.get("type") == "shortcut" and b.get("data", {}).get("shortcut_name") in removed)]
				)
			except ValueError:
				pass
			changed = True

		if changed:
			ws.flags.ignore_links = True
			ws.flags.ignore_validate = True
			ws.save(ignore_permissions=True)
			print(f"Workspace {name}: removed broken links/shortcuts {sorted(removed) or ''}")
