"""Generate Frappe 16 desk files (desktop tile, Dock, Sidebars) for the future app.

SPEC is the source of truth. Edit it, then from apps/future/ run:
    python3 scripts/gen_desk.py && bench --site <site> migrate
Recipe: Frappe 16.5x desk layout (Desktop Icon + Dock + Sidebar).
"""
import datetime, json, os, re

SPEC = {
    "app": "future",
    "app_title": "Future",
    "logo": "/assets/future/images/future-logo.svg",
    "tiles": [
        {"label": "Future", "link": "auto"},
        {"label": "Hostels", "link": "/desk/hostels", "logo": "/assets/future/images/hostel-logo.svg"},
    ],
    "rail": [
        {
            "title": "Leads",
            "owns": ["Leads", "lead-dashboard", "Lead", "Opportunity", "Lead Handover", "Lead Settings", "Team Heirarchy"],
            "module": "Future Leads",
            "icon": "handshake",
            "roles": ["Sales User", "Sales Manager", "System Manager"],
            "pins": [
                ("page", "Lead Dashboard", "lead-dashboard", "Blue", None, None),
                ("doctype", "My Open Leads", "Lead", "Blue", "{} Open", [["Lead", "status", "not in", ["Converted Student", "Lost", "Disqualified", "Invalid", "Close Lead", "Won"]]]),
                ("doctype", "Opportunities", "Opportunity", "Cyan", "{} Open", [["Opportunity", "status", "not in", ["Converted", "Converted Student", "Lost", "Closed"]]]),
                ("doctype", "Follow-ups", "ToDo", "Orange", "{} Open", [["ToDo", "status", "=", "Open"], ["ToDo", "reference_type", "=", "Lead"]]),
                ("doctype", "Hand-over Requests", "Lead Handover", "Yellow", "{} Waiting", [["Lead Handover", "docstatus", "=", 0], ["Lead Handover", "request_status", "=", "Requested"]]),
                ("doctype", "Hand-overs", "Lead Handover", "Grey", None, None),
            ],
            "items": [
                ("workspace", "Home", "Leads", "home"),
                ("page", "Dashboard", "lead-dashboard", "layout-dashboard"),
                ("doctype", "Lead", "Lead", "users-round"),
                ("doctype", "Opportunity", "Opportunity", "lightbulb"),
                ("doctype", "Follow-ups", "ToDo", "list-todo", {"reference_type": "Lead", "status": "Open"}),
                ("doctype", "Hand-overs", "Lead Handover", "arrow-right-left"),
                ("section", "Reports", "chart-column", [
                    ("report", "Total Leads", "Total Leads Report"),
                    ("report", "Team Lead Wise", "Team Lead Wise Report"),
                    ("report", "Lead Manager Wise", "Lead Manager Wise Report"),
                    ("report", "Lead Manager Totals", "Total Count Lead Manager Wise Report"),
                    ("report", "My Lead Tasks", "Lead Userwise Report"),
                    ("report", "Task Status", "Total Tasks Status Report"),
                ]),
                ("section", "Setup", "settings", [
                    ("doctype", "Team Hierarchy", "Team Heirarchy"),
                    ("doctype", "Lead Settings", "Lead Settings"),
                    ("doctype", "Lead Source", "UTM Source"),
                    ("doctype", "Discount", "Discount"),
                    ("doctype", "Base of Discount", "Base of Discount"),
                ]),
            ],
        },
        {
            "title": "Admissions",
            "owns": ["Admissions", "Program Enrollment", "Student", "Center", "Admission Settings", "Program", "Discount"],
            "module": "Future Admissions",
            "icon": "graduation-cap",
            "roles": ["Sales Manager", "System Manager", "Accounts User", "Academics User"],
            "pins": [
                ("doctype", "Pending Joining", "Program Enrollment", "Orange", "{} Pending", [["Program Enrollment", "docstatus", "=", 1], ["Program Enrollment", "custom_admission_status", "=", "Pending"]]),
                ("doctype", "Joined", "Program Enrollment", "Green", "{} Joined", [["Program Enrollment", "docstatus", "=", 1], ["Program Enrollment", "custom_admission_status", "=", "Joined"]]),
                ("doctype", "Fees Overdue", "Program Enrollment", "Red", "{} Overdue", [["Program Enrollment", "docstatus", "=", 1], ["Enrollment Fee Schedule", "status", "=", "Overdue"]]),
                ("doctype", "Payments to Approve", "Payment Approval Log", "Yellow", "{} Pending", [["Payment Approval Log", "docstatus", "=", 0]]),
                ("doctype", "Students", "Student", "Blue", None, None),
                ("doctype", "Programs", "Program", "Grey", None, None),
            ],
            "items": [
                ("workspace", "Home", "Admissions", "home"),
                ("doctype", "Admissions", "Program Enrollment", "clipboard-check"),
                ("doctype", "Students", "Student", "users"),
                ("doctype", "Payment Approval", "Payment Approval Log", "badge-check"),
                ("doctype", "Student Service", "Student Service", "receipt"),
                ("section", "Setup", "settings", [
                    ("doctype", "Program", "Program"),
                    ("doctype", "Centre", "Center"),
                    ("doctype", "Discount", "Discount"),
                    ("doctype", "Admission Settings", "Admission Settings"),
                ]),
            ],
        },
        {
            "title": "Hostels",
            "owns": ["Hostels", "Hostel", "Hostel Occupancy", "Hostel Fee Collection", "Vehicle Fee"],
            "module": "Future Hostels",
            "icon": "bed-double",
            "roles": ["Sales Manager", "System Manager", "Accounts User", "Academics User"],
            "pins": [
                ("report", "Occupancy", "Hostel Occupancy", "Blue", None, None),
                ("report", "Fee Collection", "Hostel Fee Collection", "Green", None, None),
                ("doctype", "Hostellers", "Program Enrollment", "Cyan", "{} in hostels", [["Program Enrollment", "docstatus", "=", 1], ["Program Enrollment", "custom_hosteller", "=", "Hosteller"], ["Program Enrollment", "custom_hostel_status", "=", "Allotted"]]),
                ("doctype", "Hostel Dues", "Program Enrollment", "Red", "{} with dues", [["Program Enrollment", "docstatus", "=", 1], ["Program Enrollment", "custom_hostel_status", "=", "Allotted"], ["Program Enrollment", "custom_hostel_balance", ">", 0]]),
                ("doctype", "Hostels", "Hostel", "Grey", "{} active", [["Hostel", "status", "=", "Active"]]),
                ("doctype", "Fee Rates", "Admission Settings", "Grey", None, None),
            ],
            "items": [
                ("workspace", "Home", "Hostels", "home"),
                ("report", "Occupancy", "Hostel Occupancy", "chart-column"),
                ("report", "Fee Collection", "Hostel Fee Collection", "wallet"),
                ("doctype", "Hostel", "Hostel", "hotel"),
                ("doctype", "Hostellers", "Program Enrollment", "users", {"custom_hosteller": "Hosteller", "custom_hostel_status": "Allotted", "docstatus": 1}),
                ("section", "Setup", "settings", [
                    ("doctype", "Transport Routes", "Vehicle Fee"),
                    ("doctype", "Fee Rates", "Admission Settings"),
                ]),
            ],
        },
        {
            "title": "Payments",
            "owns": ["Payments", "Payment Approval Log", "Student Service", "Sales Invoice", "Payment Entry", "App Access Approval Log"],
            "module": "Future Payments",
            "icon": "wallet",
            "roles": ["Sales Manager", "System Manager", "Accounts User", "Accounts Manager"],
            "pins": [
                ("doctype", "To Approve", "Payment Approval Log", "Yellow", "{} Pending", [["Payment Approval Log", "docstatus", "=", 0]]),
                ("doctype", "Approved", "Payment Approval Log", "Green", None, [["Payment Approval Log", "docstatus", "=", 1]]),
                ("doctype", "Student Service", "Student Service", "Blue", None, None),
                ("doctype", "Sales Invoices", "Sales Invoice", "Grey", None, None),
                ("doctype", "Payment Entries", "Payment Entry", "Grey", None, None),
            ],
            "items": [
                ("workspace", "Home", "Payments", "home"),
                ("doctype", "Payment Approval", "Payment Approval Log", "badge-check"),
                ("doctype", "Student Service", "Student Service", "clipboard-check"),
                ("doctype", "Sales Invoice", "Sales Invoice", "receipt"),
                ("doctype", "Payment Entry", "Payment Entry", "credit-card"),
                ("doctype", "App Access", "App Access Approval Log", "smartphone"),
                ("section", "Setup", "settings", [
                    ("doctype", "Hostel", "Hostel"),
                    ("doctype", "Vehicle Fee", "Vehicle Fee"),
                    ("doctype", "Program", "Program"),
                ]),
            ],
        },
    ],
}

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
ROOT = SPEC["app"]
scrub = lambda s: s.replace(" ", "_").replace("-", "_").lower()
slug = lambda s: re.sub(r"\s+", "-", s.lower().replace("&", " and ").strip())
FLAGS = {"added": 0, "child": 0, "collapsible": 1, "hidden": 0, "indent": 0,
         "is_default_module": 0, "keep_closed": 0, "open_in_new_tab": 0, "show_arrow": 0}
TYPES = {"doctype": "DocType", "report": "Report", "workspace": "Workspace",
         "page": "Page", "dashboard": "Dashboard"}


def meta(doctype, name):
    return {"app": SPEC["app"], "creation": NOW, "modified": NOW, "docstatus": 0, "idx": 0,
            "doctype": doctype, "name": name, "owner": "Administrator",
            "modified_by": "Administrator", "standard": 1}


def dump(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print("wrote", path)


def link(kind, label, target, icon=None, filters=None, child=0):
    """filters: preset list filters for a DocType link; it opens in the same window (unlike a URL link)."""
    row = {**FLAGS, "type": "Link", "label": label, "child": child}
    if filters:
        row["route_options"] = json.dumps(filters)
    if kind == "url":
        row.update(link_type="URL", url=target)
    else:
        row.update(link_type=TYPES[kind], link_to=target)
    if icon:
        row["icon"] = icon
    return row


def rows(items):
    out = []
    for it in items:
        if it[0] == "section":
            _, label, icon, children = it
            out.append({**FLAGS, "type": "Section Break", "label": label, "icon": icon,
                        "link_type": "DocType", "indent": 1, "keep_closed": 1})
            out += [link(*c, child=1) for c in children]
        else:
            out.append(link(*it))
    return [{"doctype": "Sidebar Item", "parentfield": "items", "parenttype": "Sidebar",
             "idx": i, **r} for i, r in enumerate(out, 1)]


bad = [r["title"] for r in SPEC["rail"] if re.search(r"[/?#%\\]", r["title"])]
assert not bad, f"unroutable characters in titles: {bad}"
assert len({slug(r["title"]) for r in SPEC["rail"]}) == len(SPEC["rail"]), "duplicate slugs"

for r in SPEC["rail"]:
    doc = meta("Sidebar", r["title"])
    items = rows(r["items"])
    for it in items:
        # claim these pages for this rail, so opening them shows this sidebar (boot.build_entity_module_map)
        if it.get("link_to") in r.get("owns", []):
            it["is_default_module"] = 1
    doc.update(title=r["title"], module=r["module"], header_icon=r["icon"], items=items)
    s = scrub(r["title"])
    dump(f"{ROOT}/{scrub(r['module'])}/sidebar/{s}/{s}.json", doc)

def workspace(r):
    """Workspace page for a rail: the route /desk/<slug> and the pinned shortcuts with live counts."""
    doc = meta("Workspace", r["title"])
    shortcuts, blocks = [], [{"id": "hdr", "type": "header", "data": {"text": f'<span class="h4"><b>{r["title"]}</b></span>', "col": 12}}]
    for kind, label, target, color, fmt, stats in r.get("pins", []):
        row = {"doctype": "Workspace Shortcut", "parentfield": "shortcuts", "parenttype": "Workspace",
               "label": label, "link_to": target, "type": TYPES.get(kind, "URL"), "color": color, "doc_view": "List" if kind == "doctype" else ""}
        if fmt:
            row["format"] = fmt
        if stats:
            row["stats_filter"] = json.dumps(stats)
        shortcuts.append(row)
        blocks.append({"id": scrub(label)[:10], "type": "shortcut", "data": {"shortcut_name": label, "col": 4}})
    for i, row in enumerate(shortcuts, 1):
        row["idx"] = i
    doc.update(label=r["title"], title=r["title"], module=r["module"], icon=r["icon"], public=1, is_hidden=0,
               type="Workspace", for_user="", parent_page="", content=json.dumps(blocks), shortcuts=shortcuts,
               links=[], charts=[], number_cards=[], quick_lists=[], custom_blocks=[],
               roles=[{"doctype": "Has Role", "parentfield": "roles", "parenttype": "Workspace", "role": x} for x in r.get("roles", [])],
               sequence_id=50 + SPEC["rail"].index(r), hide_custom=0)
    doc.pop("standard", None)
    s = scrub(r["title"])
    dump(f"{ROOT}/{scrub(r['module'])}/workspace/{s}/{s}.json", doc)


for r in SPEC["rail"]:
    workspace(r)

dock = meta("Dock", SPEC["app"])
dock.update(user="", items=[{"added": 0, "hidden": 0, "icon": r["icon"], "link_type": "Sidebar",
                             "link_to": r["title"], "title": r["title"]} for r in SPEC["rail"]])
dump(f"{ROOT}/dock/{SPEC['app']}/{SPEC['app']}.json", dock)

first_url = "/desk/" + slug(SPEC["rail"][0]["title"])
for n, t in enumerate(SPEC["tiles"]):
    tile = meta("Desktop Icon", t["label"])
    tile.update(label=t["label"], icon_type="App", link_type="External", hidden=0, idx=20 + n,
                link=first_url if t["link"] == "auto" else t["link"],
                logo_url=t.get("logo", SPEC["logo"]), roles=[])
    dump(f"{ROOT}/desktop_icon/{scrub(t['label'])}.json", tile)

print(f"\nSet hooks.add_to_apps_screen route to: {first_url}")
