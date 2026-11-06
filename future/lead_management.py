"""Lead hand-over: moving leads between salespeople, with an audit trail.

One code path for every way leads change hands (the Lead Handover document,
the list-view actions, the Assign To dialog), so the rules are the same:

- Who may move a lead: Sales/System Managers anything; Lead Managers and Team
  Leads only leads they can see, and only to people in their own teams.
  Salespeople (Lead Users) cannot move leads.
- What moves: the previous holder's open ToDos on the lead (assignment and
  dated follow-ups keep their dates) go to the new person, so the previous
  holder stops seeing the lead. Open Opportunities made from the lead follow it.
- Every move leaves a comment on the lead naming who moved it, from whom, to
  whom and why.
"""

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, getdate, now_datetime, nowdate

from future.permissions.visibility import get_visible_users, is_unrestricted

ROLE_FIELDS = {
	"Lead User": "custom_lead_user",
	"Team Lead": "custom_team_leader",
	"Lead Manager": "custom_lead_manager_name",
}

# ----------------------------------------------------------------------------- who may do what


def is_head(user=None):
	user = user or frappe.session.user
	return bool(frappe.db.exists("Team Heirarchy", {"user": user}))


def can_manage_leads(user=None):
	user = user or frappe.session.user
	return is_unrestricted(user) or is_head(user)


def assignable_users(user=None):
	"""People `user` may hand leads to; None means anyone."""
	user = user or frappe.session.user
	if is_unrestricted(user):
		return None
	if not is_head(user):
		return set()
	return set(get_visible_users(user))


def check_can_hand_over(lead, to_user, actor=None):
	actor = actor or frappe.session.user
	if not can_manage_leads(actor):
		frappe.throw(
			_("Only Team Leads, Lead Managers and Sales Managers can hand over leads."),
			frappe.PermissionError,
		)
	if not frappe.has_permission("Lead", "read", lead, user=actor):
		frappe.throw(_("You cannot see Lead {0}.").format(lead), frappe.PermissionError)
	allowed = assignable_users(actor)
	if allowed is not None and to_user not in allowed:
		frappe.throw(
			_("{0} is not in your team, so you cannot hand leads to them.").format(
				frappe.bold(frappe.utils.get_fullname(to_user))
			),
			frappe.PermissionError,
		)
	if not frappe.db.get_value("User", to_user, "enabled"):
		frappe.throw(_("User {0} is disabled.").format(to_user))


def heads_of(user):
	"""Team Leads and Lead Managers above `user` (any depth)."""
	heads, queue = set(), [user]
	while queue:
		for head in frappe.db.sql_list(
			"""select th.user from `tabTeam Heirarchy` th
			inner join `tabTeam Heirarchy Table` tht on tht.parent = th.name
			where tht.user = %s and ifnull(tht.active, 0) = 1""",
			queue.pop(),
		):
			if head not in heads and head != user:
				heads.add(head)
				queue.append(head)
	return heads


def validate_todo_assignment(doc, method=None):
	"""ToDo validate hook: lead/opportunity assignments follow the hand-over rules.

	Applies to every way a ToDo is made (Assign To sidebar, bulk assign, New Task,
	imports), not only our own screens. Salespeople may give tasks to themselves
	or escalate to their own heads; heads only within their teams."""
	if not doc.is_new() or doc.reference_type not in ("Lead", "Opportunity"):
		return
	if doc.assignment_rule or frappe.flags.in_import or frappe.flags.in_migrate or frappe.flags.in_install:
		return
	actor = frappe.session.user
	if not doc.allocated_to or doc.allocated_to == actor or is_unrestricted(actor):
		return
	allowed = assignable_users(actor) or set()
	allowed |= heads_of(actor)
	if doc.allocated_to not in allowed:
		frappe.throw(
			_("You cannot assign this {0} to {1}: they are not in your team.").format(
				_(doc.reference_type), frappe.bold(frappe.utils.get_fullname(doc.allocated_to))
			),
			frappe.PermissionError,
		)


# ----------------------------------------------------------------------------- the move


def current_holders(lead, role="Lead User"):
	"""Users currently holding `lead` in `role` (legacy ToDos without a role count as Lead User)."""
	role_filter = "t.custom_lead_role = %(role)s"
	if role == "Lead User":
		role_filter = "(t.custom_lead_role = %(role)s or ifnull(t.custom_lead_role, '') = '')"
	return frappe.db.sql_list(
		f"""select distinct t.allocated_to from `tabToDo` t
		where t.reference_type = 'Lead' and t.reference_name = %(lead)s
		and t.status = 'Open' and {role_filter}""",
		{"lead": lead, "role": role},
	)


def _move_todos(reference_type, reference_name, from_user, to_user, role):
	"""Give `from_user`'s open ToDos on a record to `to_user`; return how many moved."""
	moved = 0
	todos = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": reference_type,
			"reference_name": reference_name,
			"allocated_to": from_user,
			"status": "Open",
		},
		fields=["name", "custom_lead_role", "date"],
	)
	has_assignment = frappe.db.exists(
		"ToDo",
		{
			"reference_type": reference_type,
			"reference_name": reference_name,
			"allocated_to": to_user,
			"status": "Open",
		},
	)
	for row in todos:
		todo = frappe.get_doc("ToDo", row.name)
		if has_assignment and not todo.date:
			# to_user already holds this record; an undated duplicate assignment adds nothing.
			todo.status = "Cancelled"
		else:
			todo.allocated_to = to_user
			if not todo.custom_lead_role:
				todo.custom_lead_role = role
			has_assignment = True
		todo.flags.ignore_permissions = True
		todo.save()
		moved += 1
	return moved


def hand_over_lead(lead, to_user, role="Lead User", reason=None, reference=None, move_opportunities=True, actor=None):
	"""Move `lead` to `to_user` in `role`. Returns the list of previous holders."""
	actor = actor or frappe.session.user
	if role not in ROLE_FIELDS:
		frappe.throw(_("Invalid role {0}").format(role))

	previous = [u for u in current_holders(lead, role) if u != to_user]

	for user in previous:
		_move_todos("Lead", lead, user, to_user, role)

	if not frappe.db.exists(
		"ToDo", {"reference_type": "Lead", "reference_name": lead, "allocated_to": to_user, "status": "Open"}
	):
		from frappe.desk.form.assign_to import _add

		_add(
			{
				"doctype": "Lead",
				"name": lead,
				"assign_to": [to_user],
				"description": _("Lead handed over to you"),
			},
			ignore_permissions=True,
		)

	frappe.db.set_value(
		"ToDo",
		{"reference_type": "Lead", "reference_name": lead, "allocated_to": to_user, "status": "Open"},
		"custom_lead_role",
		role,
	)

	updates = {ROLE_FIELDS[role]: to_user}
	if role == "Lead User":
		updates.update(lead_owner=to_user, custom_assigned_on=now_datetime(), custom_sla_alerted_on=None)
	frappe.db.set_value("Lead", lead, updates)

	if move_opportunities:
		for opp in frappe.get_all(
			"Opportunity",
			filters={"opportunity_from": "Lead", "party_name": lead, "status": ["not in", ["Lost", "Closed", "Converted"]]},
			pluck="name",
		):
			for user in previous:
				_move_todos("Opportunity", opp, user, to_user, role)
			if role == "Lead User":
				frappe.db.set_value("Opportunity", opp, "opportunity_owner", to_user)

	from_names = ", ".join(frappe.utils.get_fullname(u) for u in previous) or _("nobody")
	text = _("{0} handed this lead over from {1} to {2} as {3}.").format(
		frappe.utils.get_fullname(actor), from_names, frappe.utils.get_fullname(to_user), _(role)
	)
	if reference:
		text += " " + _("Hand-over: {0}.").format(frappe.get_desk_link("Lead Handover", reference))
	if reason:
		text += " " + _("Reason: {0}").format(frappe.utils.escape_html(reason))
	frappe.get_doc("Lead", lead).add_comment("Info", text)

	if role == "Team Lead":
		maybe_auto_assign(lead)

	return previous


# ----------------------------------------------------------------------------- API used by the UI


@frappe.whitelist()
def get_handover_context():
	"""What the hand-over dialogs need: may the user move leads, and to whom."""
	user = frappe.session.user
	allowed = assignable_users(user)
	if allowed is None:
		users = frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]},
			fields=["name", "full_name"],
			order_by="full_name asc",
		)
	else:
		users = frappe.get_all(
			"User",
			filters={"enabled": 1, "name": ["in", list(allowed) or [""]]},
			fields=["name", "full_name"],
			order_by="full_name asc",
		)
	return {
		"can_manage": can_manage_leads(user),
		"users": [{"value": u.name, "label": u.full_name or u.name} for u in users],
	}


@frappe.whitelist()
def get_leads_held_by(user, role="Lead User", statuses=None, limit=None, oldest_first=1):
	"""Leads `user` currently holds, for picking "N of them" in a hand-over."""
	if not can_manage_leads():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	allowed = assignable_users()
	if allowed is not None and user not in allowed:
		frappe.throw(_("{0} is not in your team.").format(user), frappe.PermissionError)

	statuses = frappe.parse_json(statuses) if statuses else []
	role_filter = "t.custom_lead_role = %(role)s"
	if role == "Lead User":
		role_filter = "(t.custom_lead_role = %(role)s or ifnull(t.custom_lead_role, '') = '')"
	cond = ""
	if statuses:
		cond = "and l.status in (" + ", ".join(frappe.db.escape(s) for s in statuses) + ")"
	limit_sql = f"limit {cint(limit)}" if cint(limit) > 0 else ""
	order = "asc" if cint(oldest_first) else "desc"
	return frappe.db.sql(
		f"""select distinct l.name, l.lead_name, l.status, l.mobile_no, l.creation
		from `tabToDo` t inner join `tabLead` l on l.name = t.reference_name
		where t.reference_type = 'Lead' and t.status = 'Open' and t.allocated_to = %(user)s
		and {role_filter} {cond}
		order by l.creation {order} {limit_sql}""",
		{"user": user, "role": role},
		as_dict=True,
	)


@frappe.whitelist()
def quick_handover(leads, to_users, role="Lead User", reason=None):
	"""Create and submit a Lead Handover from the list view.

	One person in `to_users` = hand over; several = distribute evenly."""
	leads = frappe.parse_json(leads) if isinstance(leads, str) else leads
	to_users = frappe.parse_json(to_users) if isinstance(to_users, str) else to_users
	if not leads or not to_users:
		frappe.throw(_("Pick at least one lead and one person."))

	doc = frappe.new_doc("Lead Handover")
	doc.handover_type = "Distribute" if len(to_users) > 1 else "Hand Over"
	doc.role = role
	doc.reason = reason
	if len(to_users) == 1:
		doc.to_user = to_users[0]
	else:
		for u in to_users:
			doc.append("targets", {"user": u})
	for lead in leads:
		doc.append("leads", {"lead": lead})
	doc.insert()
	doc.submit()
	return {"name": doc.name, "count": len(doc.leads)}


def stamp(doc):
	doc.handed_over_by = frappe.session.user
	doc.handover_on = now_datetime()


# ----------------------------------------------------------------------------- auto-assignment


def _open_lead_count(user):
	return frappe.db.sql(
		"""select count(distinct reference_name) from `tabToDo`
		where reference_type = 'Lead' and status = 'Open' and allocated_to = %s""",
		user,
	)[0][0]


def maybe_auto_assign(lead):
	"""Give `lead` to a salesperson of its Team Lead's team, if that team auto-assigns
	and nobody holds the lead as Lead User yet. Returns the chosen user or None."""
	team_lead = frappe.db.get_value("Lead", lead, "custom_team_leader")
	if not team_lead:
		return None
	team = frappe.db.get_value(
		"Team Heirarchy",
		{"user": team_lead, "role": "Team Lead", "auto_assign": 1},
		["name", "assign_method", "max_open_leads", "last_assigned_user"],
		as_dict=True,
	)
	if not team:
		return None
	heads = {team_lead} | heads_of(team_lead)
	if [u for u in current_holders(lead, "Lead User") if u not in heads]:
		return None

	members = frappe.db.sql_list(
		"""select tht.user from `tabTeam Heirarchy Table` tht
		inner join `tabUser` u on u.name = tht.user and u.enabled = 1
		where tht.parent = %s and ifnull(tht.active, 0) = 1 order by tht.idx""",
		team.name,
	)
	loads = {m: _open_lead_count(m) for m in members}
	if cint(team.max_open_leads):
		members = [m for m in members if loads[m] < cint(team.max_open_leads)]
	if not members:
		frappe.get_doc("Lead", lead).add_comment(
			"Info", _("Auto-assign skipped: every salesperson in the team is at the open-lead limit.")
		)
		return None

	if team.assign_method == "Round Robin":
		i = members.index(team.last_assigned_user) + 1 if team.last_assigned_user in members else 0
		pick = members[i % len(members)]
	else:
		pick = min(members, key=lambda m: (loads[m], members.index(m)))

	frappe.db.set_value("Team Heirarchy", team.name, "last_assigned_user", pick, update_modified=False)
	hand_over_lead(lead, pick, "Lead User", reason=_("Auto-assigned ({0})").format(_(team.assign_method)), actor=team_lead)
	return pick


def on_lead_update(doc, method=None):
	"""Lead on_update: auto-assign when a Team Lead is set and no salesperson holds it."""
	if doc.custom_team_leader and (doc.is_new() or doc.has_value_changed("custom_team_leader")):
		maybe_auto_assign(doc.name)


def on_todo_insert(doc, method=None):
	"""Start the first-call clock when a lead is assigned to a salesperson by any path."""
	if doc.reference_type != "Lead" or doc.status != "Open" or doc.custom_lead_role not in (None, "", "Lead User"):
		return
	if frappe.db.exists("Team Heirarchy", {"user": doc.allocated_to}):
		return
	if frappe.db.get_value("Lead", doc.reference_name, "custom_lead_user") == doc.allocated_to:
		return  # a salesperson's own follow-up task must not restart the first-call clock
	frappe.db.set_value(
		"Lead",
		doc.reference_name,
		{"custom_assigned_on": now_datetime(), "custom_sla_alerted_on": None, "custom_lead_user": doc.allocated_to},
		update_modified=False,
	)


# ----------------------------------------------------------------------------- SLA and digest


def _settings():
	return frappe.get_cached_doc("Lead Settings")


def _untouched_statuses(settings):
	return [s.strip() for s in (settings.untouched_statuses or "Lead\nNew").split("\n") if s.strip()]


def late_first_call_condition(alias="l", settings=None):
	settings = settings or _settings()
	cutoff = add_to_date(now_datetime(), hours=-cint(settings.first_call_hours or 24))
	statuses = ", ".join(frappe.db.escape(s) for s in _untouched_statuses(settings))
	return f"({alias}.status in ({statuses}) and {alias}.custom_assigned_on < '{cutoff}')"


def _notify(users, subject, document_type=None, document_name=None, from_user=None):
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	users = [u for u in set(users) if u and frappe.db.get_value("User", u, "enabled")]
	if not users:
		return
	enqueue_create_notification(
		users,
		{
			"type": "Alert",
			"subject": subject,
			"document_type": document_type,
			"document_name": document_name,
			"from_user": from_user or "Administrator",
		},
	)


def check_first_call_sla():
	"""Hourly: alert the salesperson and their heads about leads not called in time (once per assignment)."""
	settings = _settings()
	if not cint(settings.sla_alerts):
		return
	rows = frappe.db.sql(
		f"""select l.name, l.lead_name, l.custom_lead_user as holder from `tabLead` l
		where {late_first_call_condition("l", settings)}
		and ifnull(l.custom_lead_user, '') != ''
		and (l.custom_sla_alerted_on is null or l.custom_sla_alerted_on < l.custom_assigned_on)
		limit 2000""",
		as_dict=True,
	)
	by_recipient = {}
	for r in rows:
		for user in {r.holder} | heads_of(r.holder):
			by_recipient.setdefault(user, []).append(r)
	hours = cint(settings.first_call_hours or 24)
	for user, leads in by_recipient.items():
		if len(leads) <= 3:
			for r in leads:
				_notify([user], _("{0} has not been called within {1} hours").format(r.lead_name or r.name, hours), "Lead", r.name)
		else:
			_notify([user], _("{0} leads have not been called within {1} hours").format(len(leads), hours))
	if rows:
		frappe.db.sql(
			"update `tabLead` set custom_sla_alerted_on = %s where name in %s",
			(now_datetime(), tuple(r.name for r in rows)),
		)


def send_daily_digest():
	"""Daily: each Team Lead / Lead Manager gets per-salesperson overdue follow-ups and late first calls."""
	settings = _settings()
	if not cint(settings.daily_digest):
		return
	late_sql = late_first_call_condition("l", settings)
	for head in frappe.get_all("Team Heirarchy", pluck="user"):
		frappe.local.future_visibility_cache = {}
		team = sorted(set(get_visible_users(head) or []) - {head})
		lines = []
		for member in team:
			overdue = frappe.db.sql(
				"""select count(*) from `tabToDo` where reference_type = 'Lead' and status = 'Open'
				and allocated_to = %s and date < %s""",
				(member, nowdate()),
			)[0][0]
			late = frappe.db.sql(
				f"select count(*) from `tabLead` l where l.custom_lead_user = %s and {late_sql}", member
			)[0][0]
			if overdue or late:
				lines.append((frappe.utils.get_fullname(member), overdue, late))
		if not lines:
			continue
		total_overdue = sum(x[1] for x in lines)
		total_late = sum(x[2] for x in lines)
		subject = _("Daily lead digest: {0} overdue follow-ups, {1} leads not called in time").format(total_overdue, total_late)
		_notify([head], subject)
		if cint(settings.digest_by_email):
			rows = "".join(f"<tr><td>{frappe.utils.escape_html(n)}</td><td>{o}</td><td>{l}</td></tr>" for n, o, l in lines)
			frappe.sendmail(
				recipients=[head],
				subject=subject,
				message=f"""<p>{_("Your team today:")}</p><table border="1" cellpadding="6" style="border-collapse:collapse">
				<tr><th>{_("Salesperson")}</th><th>{_("Overdue follow-ups")}</th><th>{_("Not called in time")}</th></tr>{rows}</table>
				<p><a href="{frappe.utils.get_url("/desk/lead-dashboard")}">{_("Open the Lead Dashboard")}</a></p>""",
			)


# ----------------------------------------------------------------------------- hand-over requests


def colleagues_of(user):
	"""Salespeople in the same team(s) as `user`."""
	out = set()
	for head in heads_of(user):
		if frappe.db.exists("Team Heirarchy", {"user": head, "role": "Team Lead"}):
			out.update(
				frappe.db.sql_list(
					"""select tht.user from `tabTeam Heirarchy Table` tht inner join `tabTeam Heirarchy` th on th.name = tht.parent
					where th.user = %s and ifnull(tht.active, 0) = 1""",
					head,
				)
			)
	out.discard(user)
	return out


@frappe.whitelist()
def get_request_context(lead=None):
	user = frappe.session.user
	users = frappe.get_all(
		"User",
		filters={"name": ["in", list(colleagues_of(user)) or [""]], "enabled": 1},
		fields=["name", "full_name"],
		order_by="full_name asc",
	)
	return {
		"can_request": bool(heads_of(user)) and (not lead or user in current_holders(lead, "Lead User")),
		"colleagues": [{"value": u.name, "label": u.full_name or u.name} for u in users],
	}


@frappe.whitelist()
def request_handover(leads, reason, to_user=None):
	"""A salesperson asks their Team Lead to move their leads (optionally to a named colleague)."""
	leads = frappe.parse_json(leads) if isinstance(leads, str) else leads
	doc = frappe.new_doc("Lead Handover")
	doc.handover_type = "Hand Over"
	doc.role = "Lead User"
	doc.to_user = to_user
	doc.reason = reason
	for lead in leads or []:
		doc.append("leads", {"lead": lead})
	doc.insert()
	return doc.name


@frappe.whitelist()
def reject_request(name, reason):
	doc = frappe.get_doc("Lead Handover", name)
	if doc.docstatus != 0 or doc.request_status != "Requested":
		frappe.throw(_("Only open requests can be rejected."))
	if not can_manage_leads() or not frappe.has_permission("Lead Handover", "write", doc):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	doc.db_set("request_status", "Rejected")
	doc.add_comment("Info", _("Rejected by {0}: {1}").format(frappe.utils.get_fullname(), frappe.utils.escape_html(reason)))
	_notify([doc.requested_by], _("Your hand-over request {0} was rejected: {1}").format(doc.name, reason), "Lead Handover", doc.name, frappe.session.user)
