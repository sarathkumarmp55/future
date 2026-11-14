"""Lead emails (sent through the default outgoing Email Account, e.g. Resend).

- New lead with nobody assigned: the Sales Managers.
- Alerts that show in the bell (hand-overs, rejected requests, first call not made in time):
  also by email.
- Every morning: each salesperson's follow-ups due today or overdue, one email per person.

Lead assignments are emailed by Frappe itself (Assignment notification). Emails only go to
people who may see the lead. Each kind can be switched off in Lead Settings.
"""

import frappe
from frappe import _
from frappe.utils import escape_html, formatdate, get_url, nowdate

MANAGER_ROLE = "Sales Manager"


def _enabled(field):
	"""Lead Settings checkboxes added later have no saved value yet: treat that as on."""
	saved = frappe.db.sql(
		"select value from `tabSingles` where doctype = 'Lead Settings' and field = %s", field
	)
	return not saved or saved[0][0] in (None, "") or bool(int(saved[0][0]))


def _recipients(users):
	out = []
	for user in set(users or []):
		if not user or user in ("Administrator", "Guest"):
			continue
		row = frappe.db.get_value("User", user, ["enabled", "email"], as_dict=True)
		if row and row.enabled and row.email:
			out.append(user)
	return sorted(out)


def render(intro, headers=None, rows=None, link=None, link_label=None):
	"""A plain email body: one sentence, an optional table, one link."""
	font = "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:14px;color:#171717"
	html = f'<div style="{font};line-height:1.5"><p style="margin:0 0 16px">{intro}</p>'
	if rows:
		th = "".join(
			f'<th align="left" style="padding:6px 12px 6px 0;border-bottom:1px solid #e2e2e2;font-weight:600">{escape_html(h)}</th>'
			for h in headers
		)
		body = "".join(
			"<tr>" + "".join(f'<td style="padding:6px 12px 6px 0;border-bottom:1px solid #f0f0f0">{c}</td>' for c in r) + "</tr>"
			for r in rows
		)
		html += f'<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;margin:0 0 16px">{th and "<tr>" + th + "</tr>"}{body}</table>'
	if link:
		html += f'<p style="margin:0"><a href="{link}" style="color:#2a78d6">{escape_html(link_label or _("Open in ERP"))}</a></p>'
	return html + "</div>"


def send(users, subject, message, reference_doctype=None, reference_name=None):
	users = _recipients(users)
	if not users:
		return
	try:
		frappe.sendmail(
			recipients=users,
			subject=subject,
			message=message,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
		)
	except Exception:
		# No outgoing Email Account yet, or it is misconfigured: an email must never stop the
		# assignment, hand-over or job that triggered it.
		frappe.clear_last_message()
		frappe.log_error(f"Lead email not sent: {subject}", reference_doctype=reference_doctype, reference_name=reference_name)


def doc_link(doctype, name):
	return get_url(f"/desk/{frappe.scrub(doctype).replace('_', '-')}/{name}")


def lead_link(lead, label=None):
	return f'<a href="{doc_link("Lead", lead)}" style="color:#2a78d6">{escape_html(label or lead)}</a>'


# ----------------------------------------------------------------------------- bell alerts by email


def email_alert(users, subject, document_type=None, document_name=None):
	if not _enabled("email_alerts"):
		return
	link = doc_link(document_type, document_name) if document_type and document_name else get_url("/desk/lead-dashboard")
	send(users, subject, render(escape_html(subject), link=link), document_type, document_name)


# ----------------------------------------------------------------------------- new unassigned lead


def on_lead_insert(doc, method=None):
	# Auto-assign runs in the same request (Lead on_update), so check after the commit.
	if frappe.flags.in_import or frappe.flags.in_patch or frappe.flags.in_install:
		return
	frappe.enqueue(
		"future.notifications.email_unassigned_lead",
		lead=doc.name,
		queue="short",
		enqueue_after_commit=True,
	)


def email_unassigned_lead(lead):
	if not _enabled("new_lead_email"):
		return
	row = frappe.db.get_value(
		"Lead",
		lead,
		["name", "lead_name", "mobile_no", "custom_course_categories", "utm_source", "_assign", "custom_lead_user"],
		as_dict=True,
	)
	if not row or row.custom_lead_user or frappe.parse_json(row._assign or "[]"):
		return
	managers = frappe.get_all(
		"Has Role", filters={"role": MANAGER_ROLE, "parenttype": "User"}, pluck="parent", distinct=True
	)
	details = [
		(_("Name"), escape_html(row.lead_name or row.name)),
		(_("Mobile"), escape_html(row.mobile_no or "-")),
		(_("Course"), escape_html(row.custom_course_categories or "-")),
		(_("Source"), escape_html(row.utm_source or "-")),
	]
	send(
		managers,
		_("New lead to assign: {0}").format(row.lead_name or row.name),
		render(
			_("A new lead came in and nobody is assigned to it yet."),
			[_("Field"), _("Value")],
			details,
			doc_link("Lead", row.name),
			_("Open the lead and assign it"),
		),
		"Lead",
		row.name,
	)


# ----------------------------------------------------------------------------- morning follow-ups


def send_followup_emails():
	"""Every morning: each salesperson's open follow-ups on their own leads, due today or earlier."""
	if not _enabled("followup_email"):
		return
	from future.permissions.visibility import lead_condition

	today = nowdate()
	users = frappe.db.sql_list(
		"""select distinct allocated_to from `tabToDo`
		where status = 'Open' and reference_type = 'Lead' and date <= %s and ifnull(allocated_to, '') != ''""",
		today,
	)
	for user in _recipients(users):
		frappe.local.future_visibility_cache = {}
		visible = lead_condition("l", user) or "1 = 1"
		rows = frappe.db.sql(
			f"""select t.date, t.description, l.name, l.lead_name, l.mobile_no
			from `tabToDo` t inner join `tabLead` l on l.name = t.reference_name
			where t.status = 'Open' and t.reference_type = 'Lead' and t.allocated_to = %s
			and t.date <= %s and {visible}
			order by t.date, l.lead_name limit 200""",
			(user, today),
			as_dict=True,
		)
		if not rows:
			continue
		overdue = sum(1 for r in rows if str(r.date) < today)
		due_today = len(rows) - overdue
		table = [
			(
				_("Overdue") + f" ({formatdate(r.date)})" if str(r.date) < today else _("Today"),
				lead_link(r.name, r.lead_name or r.name),
				escape_html(r.mobile_no or "-"),
				escape_html(frappe.utils.strip_html(r.description or ""))[:120],
			)
			for r in rows
		]
		send(
			[user],
			_("Follow-ups today: {0} due, {1} overdue").format(due_today, overdue),
			render(
				_("Good morning {0}. These follow-ups are waiting for you:").format(
					escape_html(frappe.utils.get_fullname(user))
				),
				[_("When"), _("Lead"), _("Mobile"), _("Note")],
				table,
				get_url("/desk/todo?status=Open&reference_type=Lead"),
				_("Open my follow-ups"),
			),
		)
