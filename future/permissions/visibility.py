"""Who can see which Lead / Opportunity.

Salespeople compete with each other, so a record is private to the people
working it and to their line managers:

- Administrator, System Manager, Sales Manager ........ everything
- Lead Manager (Team Heirarchy) ....................... own + their team leads + those team leads' users
- Team Lead (Team Heirarchy) .......................... own + their active team users
- Everyone else (Lead User) ........................... only records assigned to them

"Own" means assigned to the user (`_assign`), or set as the record's
Team Lead / Lead Manager, or created by them while nobody is assigned. A creator
loses sight of a lead once it is handed to someone else, so leads moved from one
salesperson to another really move.
"""

import frappe

UNRESTRICTED_ROLES = {"System Manager", "Sales Manager"}

# Lead fields naming the heads responsible for it. The Lead User is deliberately
# not here: a salesperson's access follows the live assignment (`_assign`) only.
LEAD_PEOPLE_FIELDS = ("custom_team_leader", "custom_lead_manager_name")


def is_unrestricted(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(UNRESTRICTED_ROLES & set(frappe.get_roles(user)))


def _team_of(head, role):
	return frappe.db.sql_list(
		"""
		select tht.user
		from `tabTeam Heirarchy` th
		inner join `tabTeam Heirarchy Table` tht on tht.parent = th.name
		where th.user = %s and th.role = %s and ifnull(tht.active, 0) = 1 and ifnull(tht.user, '') != ''
		""",
		(head, role),
	)


def get_visible_users(user=None):
	"""Users whose records `user` may see, or None when `user` sees everything."""
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None

	cache = getattr(frappe.local, "future_visibility_cache", None)
	if cache is None:
		cache = frappe.local.future_visibility_cache = {}
	if user in cache:
		return cache[user]

	users = {user}
	team_leads = _team_of(user, "Lead Manager")
	users.update(team_leads)
	for tl in team_leads:
		users.update(_team_of(tl, "Team Lead"))
	users.update(_team_of(user, "Team Lead"))

	cache[user] = users
	return users


def _quote_json_member(user):
	"""LIKE pattern matching `"user"` inside a JSON list (the quotes stop a@x.com matching aa@x.com)."""
	escaped = user.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return frappe.db.escape(f'%"{escaped}"%')


def record_condition(table, users, people_fields=()):
	"""SQL condition limiting `table` (e.g. "`tabLead`" or an alias) to records of `users`."""
	if not users:
		return "1 = 0"

	in_list = ", ".join(frappe.db.escape(u) for u in sorted(users))
	parts = [f"{table}.`_assign` like {_quote_json_member(u)}" for u in sorted(users)]
	parts += [f"{table}.`{field}` in ({in_list})" for field in people_fields]
	parts.append(f"({table}.`owner` in ({in_list}) and ifnull({table}.`_assign`, '') in ('', '[]'))")
	return "(" + " or ".join(parts) + ")"


def lead_condition(table="`tabLead`", user=None):
	"""Condition for raw SQL on Lead; None when the user sees everything."""
	users = get_visible_users(user)
	if users is None:
		return None
	return record_condition(table, users, LEAD_PEOPLE_FIELDS)


def can_see(doc, users, people_fields=()):
	if users is None:
		return True
	if doc.get("__islocal") or doc.is_new():
		return True
	assigned = set(frappe.parse_json(doc.get("_assign") or "[]") or [])
	if assigned & users:
		return True
	if any(doc.get(f) in users for f in people_fields):
		return True
	return doc.get("owner") in users and not assigned


# ----------------------------------------------------------------------------- hooks


def lead_query_conditions(user=None):
	return lead_condition("`tabLead`", user) or ""


def lead_has_permission(doc, ptype=None, user=None, debug=False):
	# frappe treats a falsy return as "deny", so always answer True/False explicitly.
	return can_see(doc, get_visible_users(user), LEAD_PEOPLE_FIELDS)


def opportunity_query_conditions(user=None):
	users = get_visible_users(user)
	if users is None:
		return ""
	return record_condition("`tabOpportunity`", users)


def opportunity_has_permission(doc, ptype=None, user=None, debug=False):
	return can_see(doc, get_visible_users(user))


# ----------------------------------------------------------------------------- contacts & addresses
#
# ERPNext links a Contact to every Lead. Without this, any Sales User could
# read every lead's name and phone number from the Contact list.


def _linked_condition(parent_doctype, table, user):
	users = get_visible_users(user)
	if users is None:
		return ""
	visible_leads = record_condition("l", users, LEAD_PEOPLE_FIELDS)
	return f"""(not exists (
			select 1 from `tabDynamic Link` dl
			where dl.parent = {table}.name and dl.parenttype = '{parent_doctype}' and dl.link_doctype = 'Lead')
		or exists (
			select 1 from `tabDynamic Link` dl inner join `tabLead` l on l.name = dl.link_name
			where dl.parent = {table}.name and dl.parenttype = '{parent_doctype}' and dl.link_doctype = 'Lead'
			and {visible_leads}))"""


def _linked_visible(doc, user):
	users = get_visible_users(user)
	if users is None or doc.is_new():
		return True
	leads = [l.link_name for l in doc.get("links") or [] if l.link_doctype == "Lead"]
	if not leads:
		return True
	return any(
		can_see(frappe.get_doc("Lead", lead), users, LEAD_PEOPLE_FIELDS)
		for lead in leads
		if frappe.db.exists("Lead", lead)
	)


def contact_query_conditions(user=None):
	return _linked_condition("Contact", "`tabContact`", user)


def contact_has_permission(doc, ptype=None, user=None, debug=False):
	return _linked_visible(doc, user)


def address_query_conditions(user=None):
	return _linked_condition("Address", "`tabAddress`", user)


def address_has_permission(doc, ptype=None, user=None, debug=False):
	return _linked_visible(doc, user)


# ----------------------------------------------------------------------------- lead hand-overs
#
# A hand-over lists lead names, so it is private like the leads: visible to the
# people who made or requested it and to their heads.


def handover_query_conditions(user=None):
	users = get_visible_users(user)
	if users is None:
		return ""
	in_list = ", ".join(frappe.db.escape(u) for u in sorted(users))
	return (
		f"(`tabLead Handover`.owner in ({in_list}) or `tabLead Handover`.requested_by in ({in_list}) "
		f"or `tabLead Handover`.handed_over_by in ({in_list}))"
	)


def handover_has_permission(doc, ptype=None, user=None, debug=False):
	users = get_visible_users(user)
	if users is None or doc.is_new():
		return True
	return bool({doc.owner, doc.get("requested_by"), doc.get("handed_over_by")} & users)
