import frappe

# Top-level sidebar workspaces every user should see; all others are hidden.
# Child workspaces follow their top-level parent.
VISIBLE_WORKSPACES = {
	"Accounting",
	"Buying",
	"Selling",
	"Stock",
	"Assets",
	"HR",
	"Education",
	"Payroll",
	"CRM",
}


def hide_unused_workspaces():
	workspaces = frappe.get_all(
		"Workspace",
		filters={"public": 1},
		fields=["name", "parent_page", "is_hidden"],
	)
	parent_of = {w.name: w.parent_page for w in workspaces}

	def root(name):
		seen = set()
		while parent_of.get(name) and name not in seen:
			seen.add(name)
			name = parent_of[name]
		return name

	for w in workspaces:
		hidden = 0 if root(w.name) in VISIBLE_WORKSPACES else 1
		if w.is_hidden != hidden:
			frappe.db.set_value("Workspace", w.name, "is_hidden", hidden, update_modified=False)

	frappe.clear_cache()
