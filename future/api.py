# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
from frappe.utils import flt

@frappe.whitelist()
def create_payment_approval_log(opportunity_name, party_name):

    opportunity = frappe.get_doc("Opportunity", opportunity_name)
    lead_name = frappe.db.get_value("Lead", party_name, "lead_name")
    lead_age = frappe.db.get_value("Lead", party_name, "custom_age")
    lead_custom_course_categories = frappe.db.get_value("Lead", party_name, "custom_course_categories")
    lead_custom_board = frappe.db.get_value("Lead", party_name, "custom_board")
    lead_gender = frappe.db.get_value("Lead", party_name, "gender")
    lead_email_id = frappe.db.get_value("Lead", party_name, "email_id")
    lead_class = frappe.db.get_value("Lead", party_name, "custom_class")
    lead_mobile_no = frappe.db.get_value("Lead", party_name, "mobile_no")

    log = frappe.get_doc({
        "doctype": "Payment Approval Log",
        "lead_reference": party_name,
        "opportunity_reference": opportunity.name,
        "student_name": lead_name,
        "age": lead_age,
        "course_category": lead_custom_course_categories,
        "board": lead_custom_board,
        "gender": opportunity.gender,
        "email_id": opportunity.email_id,
        "location": opportunity.custom_location,
        "transaction_date": opportunity.custom_payment_date,
        "transaction_id": opportunity.custom_transaction_id,
        "academic_year": opportunity.custom_academic_year,
        "mode_of_payment": opportunity.custom_mode_of_payment,
        "account_paid_to": opportunity.custom_account_paid_to,
        "class": lead_class,
        "mobile_number": lead_mobile_no,
        "date": frappe.utils.today(),
        "from_opportunity": 1,
        "attach": opportunity.custom_attach_screenshot,
        "discount_applied": opportunity.custom_discount_approved,
        "discount_id": opportunity.custom_discount_id,
    })

    if opportunity.custom_fees == 1:
        log.fees = 1
        log.program = opportunity.custom_program
        log.fees_received_amount = opportunity.custom_program_received_amount
        log.total_amount = opportunity.custom_program_total_amount
        # log.total_gst_amount = opportunity.custom_total_amount_gst
        for row in opportunity.custom_fees_details:
            log.append("fee_details", {
                "components": row.components,
                "amount": row.amount,
                "received_amount": row.received_amount
            })

    if opportunity.custom_hostel_required == 1:
        log.hostel_required = 1
        log.hostel = opportunity.custom_hostel
        log.hostel_total_amount = opportunity.custom_hostel_total_amount
        log.hostel_received_amount = opportunity.custom_hostel_received_amount
        for row in opportunity.custom_hostel_components:
            log.append("hostel_components", {
                "components": row.components,
                "amount": row.amount,
                "received_amount": row.received_amount
            })

    if opportunity.custom_vehicle_required == 1:
        log.vehicle_required = 1
        log.vehicle = opportunity.custom_vehicle
        log.vehicle_total_amount = opportunity.custom_vehicle_total_amount
        log.vehicle_received_amount = opportunity.custom_vehicle_received_amount
        for row in opportunity.custom_vehicle_components:
            log.append("vehicle_components", {
                "components": row.components,
                "amount": row.amount,
                "received_amount": row.received_amount
            })

    log.total_bill_amount = (
        flt(log.fees_received_amount)
        + flt(log.hostel_received_amount)
        + flt(log.vehicle_received_amount)
    )

    log.insert(ignore_permissions=True)
    if party_name:
        frappe.db.set_value(
            "Lead",
            party_name,
            "status",
            "Payment Approval Pending"
        )

    frappe.db.set_value(
        "Opportunity",
        opportunity.name,
        "status",
        "Payment Approval Pending"
    )

    frappe.db.commit()

    return log.name



import frappe


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_team_heirarchy_users(doctype, txt, searchfield, start, page_len, filters):
    role = (filters or {}).get("role")
    return frappe.db.sql(
        """
        select u.name, u.full_name
        from `tabTeam Heirarchy` th
        inner join `tabUser` u on u.name = th.user
        where (ifnull(%(role)s, '') = '' or th.role = %(role)s)
          and ifnull(u.enabled, 1) = 1
          and (u.name like %(txt)s or u.full_name like %(txt)s)
        order by u.full_name
        limit %(start)s, %(page_len)s
        """,
        {
            "role": role,
            "txt": "%" + (txt or "") + "%",
            "start": start,
            "page_len": page_len,
        },
    )


@frappe.whitelist()
def is_team_lead(user=None):
    user = user or frappe.session.user
    return bool(frappe.db.exists("Team Heirarchy", {"user": user, "role": "Team Lead"}))


@frappe.whitelist()
def is_lead_manager(user=None):
    user = user or frappe.session.user
    return bool(frappe.db.exists("Team Heirarchy", {"user": user, "role": "Lead Manager"}))


@frappe.whitelist()
def get_team_lead_users(team_lead=None, role="Team Lead"):
    team_lead = team_lead or frappe.session.user
    rows = frappe.db.sql(
        """
        select tht.user, ifnull(u.full_name, tht.user) as full_name
        from `tabTeam Heirarchy` th
        inner join `tabTeam Heirarchy Table` tht on tht.parent = th.name
        left join `tabUser` u on u.name = tht.user
        where th.user = %(team_lead)s
          and th.role = %(role)s
          and ifnull(tht.active, 0) = 1
        order by full_name
        """,
        {"team_lead": team_lead, "role": role or "Team Lead"},
        as_dict=1,
    )
    return [{"value": r.user, "label": r.full_name} for r in rows if r.user]


@frappe.whitelist()
def set_lead_assignment_role(doctype, names, allocated_to, role):
    """Called by the Assign To dialog after it assigned `names` to `allocated_to`.

    Lead assignments are hand-overs (future.lead_management.hand_over_lead):
    whoever held `role` before loses the lead, and the move is commented on it.
    """
    from future.lead_management import ROLE_FIELDS, check_can_hand_over, hand_over_lead

    if role not in ROLE_FIELDS:
        frappe.throw("Invalid Role")

    if isinstance(names, str):
        names = frappe.parse_json(names)

    for name in names or []:
        if doctype == "Lead":
            check_can_hand_over(name, allocated_to)
            hand_over_lead(name, allocated_to, role, reason=frappe._("Assigned from the list"))
        else:
            frappe.has_permission(doctype, "write", name, throw=True)
            frappe.db.set_value(
                "ToDo",
                {"reference_type": doctype, "reference_name": name, "allocated_to": allocated_to, "status": "Open"},
                "custom_lead_role",
                role,
            )

    return True


@frappe.whitelist()
def get_students_without_app_access():
    return frappe.get_all(
        "Student",
        filters={"custom_app_access_provided": 0},
        fields=["name", "student_name", "first_name"],
        order_by="name",
    )


@frappe.whitelist()
def provide_app_access(student, transaction_id=None):
    if not student:
        frappe.throw("Student is required")

    update = {"custom_app_access_provided": 1}
    if transaction_id:
        update["custom_app_access_transaction_id"] = transaction_id

    frappe.db.set_value("Student", student, update)
    frappe.db.commit()

    return {"success": True}


@frappe.whitelist()
def provide_app_access_bulk(students, transaction_id=None):
    if isinstance(students, str):
        students = frappe.parse_json(students)

    if not students:
        frappe.throw("No students selected")

    update = {"custom_app_access_provided": 1}
    if transaction_id:
        update["custom_app_access_transaction_id"] = transaction_id

    for student in students:
        frappe.db.set_value("Student", student, update)

    frappe.db.commit()

    return {"success": True, "count": len(students)}