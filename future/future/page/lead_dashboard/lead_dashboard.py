"""Data for the Lead Dashboard page.

Everything is scoped by future.permissions.visibility, so a salesperson only
ever sees numbers for their own leads. The team table (who is converting
best) is shown only to Team Leads, Lead Managers and Sales/System Managers,
because salespeople compete with each other.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, nowdate

from future.permissions.visibility import get_visible_users, is_unrestricted, lead_condition, record_condition

from future.lead_stages import STAGES, late_filters, stage_statuses


def _in(values):
	return "(" + ", ".join(frappe.db.escape(v) for v in values) + ")"


STAGE_SQL = f"""case
	when l.status in {_in(STAGES['Won'])} then 'Won'
	when l.status in {_in(STAGES['Lost'])} then 'Lost'
	when l.status in {_in(STAGES['Interested'])} then 'Interested'
	when l.status in {_in(STAGES['Contacted'])} then 'Contacted'
	else 'New' end"""


def _role_of(user):
	if is_unrestricted(user):
		return "manager"
	if frappe.db.exists("Team Heirarchy", {"user": user, "role": "Lead Manager"}):
		return "lead_manager"
	if frappe.db.exists("Team Heirarchy", {"user": user, "role": "Team Lead"}):
		return "team_lead"
	return "lead_user"


def _period(filters):
	to_date = getdate(filters.get("to_date") or nowdate())
	from_date = getdate(filters.get("from_date") or add_days(to_date, -29))
	if from_date > to_date:
		from_date, to_date = to_date, from_date
	return from_date, to_date


def _member_condition(member):
	pattern = member.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return "l._assign like " + frappe.db.escape(f'%"{pattern}"%')


def _where(filters, from_date, to_date, member=None, with_dates=True):
	cond = ["1 = 1"]
	visible = lead_condition("l")
	if visible:
		cond.append(visible)
	if with_dates:
		cond.append(f"l.creation >= '{from_date} 00:00:00' and l.creation <= '{to_date} 23:59:59'")
	if filters.get("source"):
		cond.append("l.utm_source = " + frappe.db.escape(filters["source"]))
	if filters.get("course_category"):
		cond.append("l.custom_course_categories = " + frappe.db.escape(filters["course_category"]))
	if filters.get("location"):
		cond.append("l.custom_location = " + frappe.db.escape(filters["location"]))
	if member:
		cond.append(_member_condition(member))
	return " and ".join(cond)


@frappe.whitelist()
def get_data(filters=None):
	filters = frappe.parse_json(filters) if filters else {}
	user = frappe.session.user
	role = _role_of(user)
	from_date, to_date = _period(filters)

	member = filters.get("member")
	visible_users = get_visible_users(user)
	if member and visible_users is not None and member not in visible_users:
		frappe.throw(_("You can only filter by members of your own team."), frappe.PermissionError)

	where = _where(filters, from_date, to_date, member)

	stage_rows = frappe.db.sql(
		f"select {STAGE_SQL} as stage, count(*) as n from `tabLead` l where {where} group by stage",
		as_dict=True,
	)
	stages = {s: 0 for s in ("New", "Contacted", "Interested", "Won", "Lost")}
	for r in stage_rows:
		stages[r.stage] = r.n
	total = sum(stages.values())

	previous = _previous_total(filters, from_date, to_date, member)

	from future.lead_management import _settings, late_first_call_condition

	settings = _settings()
	late = frappe.db.sql(
		f"select count(*) from `tabLead` l where {_where(filters, from_date, to_date, member, with_dates=False)} "
		f"and {late_first_call_condition('l', settings)}"
	)[0][0]

	return {
		"role": role,
		"period": {"from_date": str(from_date), "to_date": str(to_date)},
		"kpis": {
			"total": total,
			"previous_total": previous,
			"contacted": stages["Contacted"] + stages["Interested"] + stages["Won"],
			"interested": stages["Interested"] + stages["Won"],
			"won": stages["Won"],
			"lost": stages["Lost"],
			"untouched": stages["New"],
			"conversion": round(stages["Won"] * 100.0 / total, 1) if total else 0,
			"late": late,
			"sla_hours": settings.first_call_hours or 24,
		},
		"stages": stages,
		"trend": _trend(where, from_date, to_date),
		"sources": _group(where, "l.utm_source"),
		"courses": _group(where, "l.custom_course_categories"),
		"locations": _group(where, "l.custom_location"),
		"followups": _followups(user),
		"team": _team(filters, from_date, to_date, visible_users) if role != "lead_user" else None,
		"members": _members(visible_users) if role != "lead_user" else [],
		"recent": _recent(where),
		"opportunities": _opportunities(from_date, to_date, member, visible_users),
		"handovers": _handovers() if role != "lead_user" else None,
		"tile_filters": _tile_filters(filters, from_date, to_date, member),
		"pending_requests": len(
			frappe.get_list("Lead Handover", filters={"docstatus": 0, "request_status": "Requested"}, pluck="name")
		)
		if role != "lead_user"
		else 0,
	}


def _previous_total(filters, from_date, to_date, member):
	days = date_diff(to_date, from_date) + 1
	prev_to = add_days(from_date, -1)
	prev_from = add_days(prev_to, -(days - 1))
	where = _where(filters, getdate(prev_from), getdate(prev_to), member)
	return frappe.db.sql(f"select count(*) from `tabLead` l where {where}")[0][0]


def _trend(where, from_date, to_date):
	rows = frappe.db.sql(
		f"""select date(l.creation) as d, count(*) as n,
			sum(l.status in {_in(STAGES['Won'])}) as won
		from `tabLead` l where {where} group by date(l.creation)""",
		as_dict=True,
	)
	by_day = {str(r.d): r for r in rows}
	out = []
	for i in range(date_diff(to_date, from_date) + 1):
		d = str(add_days(from_date, i))
		r = by_day.get(d)
		out.append({"date": d, "leads": r.n if r else 0, "won": int(r.won or 0) if r else 0})
	return out


def _group(where, column, limit=8):
	rows = frappe.db.sql(
		f"""select coalesce(nullif({column}, ''), 'Not set') as label, count(*) as n,
			sum(l.status in {_in(STAGES['Won'])}) as won
		from `tabLead` l where {where} group by label order by n desc""",
		as_dict=True,
	)
	for r in rows:
		r.won = int(r.won or 0)
	if len(rows) > limit:
		rest = rows[limit - 1 :]
		rows = rows[: limit - 1] + [
			frappe._dict(label="Other", n=sum(r.n for r in rest), won=sum(r.won for r in rest))
		]
	return rows


def _followups(user):
	"""The signed-in user's own open lead tasks: overdue, due today, upcoming."""
	rows = frappe.db.sql(
		"""select t.name, t.date, t.description, t.reference_name as lead,
			l.lead_name, l.mobile_no, l.status
		from `tabToDo` t
		inner join `tabLead` l on l.name = t.reference_name
		where t.reference_type = 'Lead' and t.status = 'Open' and t.allocated_to = %s
		order by ifnull(t.date, '2999-12-31'), t.creation
		limit 200""",
		user,
		as_dict=True,
	)
	today = getdate(nowdate())
	counts = {"overdue": 0, "today": 0, "upcoming": 0}
	for r in rows:
		if r.date and getdate(r.date) < today:
			r.when = "overdue"
		elif r.date and getdate(r.date) == today:
			r.when = "today"
		else:
			r.when = "upcoming"
		counts[r.when] += 1
		r.description = frappe.utils.strip_html(r.description or "")[:140]
	return {"counts": counts, "items": [r for r in rows if r.when != "upcoming"][:12]}


def _members(visible_users):
	users = visible_users
	if users is None:
		users = set(
			frappe.db.sql_list(
				"select distinct allocated_to from `tabToDo` where reference_type = 'Lead' and status = 'Open'"
			)
		)
	rows = frappe.get_all(
		"User",
		filters={"name": ["in", list(users) or [""]], "enabled": 1},
		fields=["name", "full_name"],
		order_by="full_name asc",
	)
	return [{"value": r.name, "label": r.full_name or r.name} for r in rows]


def _team(filters, from_date, to_date, visible_users):
	"""Per-salesperson results for heads. Counts leads by the person they are assigned to."""
	where = _where(filters, from_date, to_date)
	user_filter = ""
	if visible_users is not None:
		user_filter = "and t.allocated_to in " + _in(sorted(visible_users))
	rows = frappe.db.sql(
		f"""select t.allocated_to as user, count(distinct l.name) as assigned,
			count(distinct case when {STAGE_SQL} in ('Contacted', 'Interested', 'Won') then l.name end) as contacted,
			count(distinct case when {STAGE_SQL} in ('Interested', 'Won') then l.name end) as interested,
			count(distinct case when {STAGE_SQL} = 'Won' then l.name end) as won,
			count(distinct case when {STAGE_SQL} = 'Lost' then l.name end) as lost
		from `tabToDo` t
		inner join `tabLead` l on l.name = t.reference_name
		where t.reference_type = 'Lead' and t.status = 'Open' and {where} {user_filter}
		group by t.allocated_to""",
		as_dict=True,
	)
	overdue = dict(
		frappe.db.sql(
			f"""select allocated_to, count(*) from `tabToDo` t
			where reference_type = 'Lead' and status = 'Open' and date < %s {user_filter}
			group by allocated_to""",
			nowdate(),
		)
	)
	names = dict(frappe.get_all("User", filters={"name": ["in", [r.user for r in rows] or [""]]}, fields=["name", "full_name"], as_list=True))
	for r in rows:
		r.full_name = names.get(r.user) or r.user
		r.overdue = overdue.get(r.user, 0)
		r.conversion = round(r.won * 100.0 / r.assigned, 1) if r.assigned else 0
	rows.sort(key=lambda r: (-r.won, -r.assigned))
	return rows


def _recent(where):
	return frappe.db.sql(
		f"""select l.name, l.lead_name, l.mobile_no, l.status, l.utm_source,
			l.custom_course_categories as course, l.creation
		from `tabLead` l where {where} order by l.creation desc limit 8""",
		as_dict=True,
	)


def _opportunities(from_date, to_date, member, visible_users):
	cond = [f"o.creation between '{from_date} 00:00:00' and '{to_date} 23:59:59'"]
	if visible_users is not None:
		cond.append(record_condition("o", visible_users))
	if member:
		cond.append(_member_condition(member).replace("l._assign", "o._assign"))
	where = " and ".join(cond)
	rows = frappe.db.sql(
		f"""select coalesce(nullif(o.status, ''), 'Open') as label, count(*) as n,
			sum(ifnull(o.opportunity_amount, 0)) as amount
		from `tabOpportunity` o where {where} group by label order by n desc""",
		as_dict=True,
	)
	closed = {"Lost", "Closed", "Converted", "Converted Student"}
	return {
		"total": sum(r.n for r in rows),
		"open": sum(r.n for r in rows if r.label not in closed),
		"open_amount": sum(r.amount for r in rows if r.label not in closed),
		"won": sum(r.n for r in rows if r.label in ("Converted", "Converted Student")),
		"by_status": [{"label": r.label, "n": r.n, "won": 0} for r in rows],
	}


def _handovers():
	rows = frappe.get_list(
		"Lead Handover",
		filters={"docstatus": 1},
		fields=["name", "handover_type", "to_user", "total_leads", "handed_over_by", "handover_on", "reason"],
		order_by="handover_on desc",
		limit_page_length=6,
	)
	for r in rows:
		r.to_name = frappe.utils.get_fullname(r.to_user) if r.to_user else _("Several people")
		r.by_name = frappe.utils.get_fullname(r.handed_over_by)
	return rows


def _tile_filters(filters, from_date, to_date, member):
	"""Lead list route options for each KPI tile, so a click shows exactly the counted leads."""
	base = {"creation": ["between", [str(from_date), str(to_date)]]}
	if filters.get("source"):
		base["utm_source"] = filters["source"]
	if filters.get("course_category"):
		base["custom_course_categories"] = filters["course_category"]
	if filters.get("location"):
		base["custom_location"] = filters["location"]
	if member:
		base["_assign"] = ["like", f'%"{member}"%']
	out = {"all": dict(base)}
	for key, stage in (("new", "New"), ("contacted", "Contacted"), ("interested", "Interested"), ("won", "Won"), ("lost", "Lost")):
		out[key] = {**base, "status": ["in", stage_statuses(stage)]}
	late = {f[1]: [f[2], f[3]] if f[2] != "is" else ["is", f[3]] for f in late_filters()}
	out["late"] = {**{k: v for k, v in base.items() if k != "creation"}, **late}
	return out
