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
    "tiles": [{"label": "Future", "link": "auto"}],
    "rail": [
        {
            "title": "Leads",
            "module": "future",
            "icon": "handshake",
            "items": [
                ("page", "Dashboard", "lead-dashboard", "layout-dashboard"),
                ("doctype", "Lead", "Lead", "users-round"),
                ("doctype", "Opportunity", "Opportunity", "lightbulb"),
                ("url", "Follow-ups", "/desk/todo?reference_type=Lead&status=Open", "list-todo"),
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
            "title": "Payments",
            "module": "future",
            "icon": "wallet",
            "items": [
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


def link(kind, label, target, icon=None, child=0):
    row = {**FLAGS, "type": "Link", "label": label, "child": child}
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
    doc.update(title=r["title"], module=r["module"], header_icon=r["icon"], items=rows(r["items"]))
    s = scrub(r["title"])
    dump(f"{ROOT}/{scrub(r['module'])}/sidebar/{s}/{s}.json", doc)

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
