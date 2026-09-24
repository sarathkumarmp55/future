import json

import frappe


def on_update(doc, method=None):
    create_todos_for_assignments(doc)


def create_todos_for_assignments(doc):
    if not doc.get("_assign"):
        return

    try:
        assignees = json.loads(doc._assign)
    except Exception:
        return

    if not isinstance(assignees, list):
        return

    for user in assignees:
        if not user or is_excluded_user(user):
            continue

        if todo_exists(doc.doctype, doc.name, user):
            continue

        todo = frappe.get_doc(
            {
                "doctype": "ToDo",
                "owner": user,
                "allocated_to": user,
                "assigned_by": frappe.session.user,
                "reference_type": doc.doctype,
                "reference_name": doc.name,
                "description": f"Lead {doc.name} assigned to you",
                "status": "Open",
                "priority": "Medium",
                "date": frappe.utils.nowdate(),
            }
        )
        todo.insert(ignore_permissions=True)


def is_excluded_user(user):
    if user == "Administrator":
        return True

    return frappe.db.exists(
        "Has Role",
        {"parent": user, "role": "Sales Manager"},
    )


def todo_exists(reference_type, reference_name, allocated_to):
    return frappe.db.exists(
        "ToDo",
        {
            "reference_type": reference_type,
            "reference_name": reference_name,
            "allocated_to": allocated_to,
            "status": ["!=", "Cancelled"],
        },
    )
