import frappe


def get_permission_query_conditions(user=None):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return None

    if frappe.db.exists(
        "Has Role",
        {"parent": user, "role": "Sales Manager"},
    ):
        return None

    escaped_user = (
        user.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

    return (
        f"(`tabLead`.`owner` = '{escaped_user}' "
        f"OR `tabLead`.`_assign` LIKE '%{escaped_user}%')"
    )
