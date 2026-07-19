# pyrefly: ignore [missing-import]
import frappe


@frappe.whitelist()
def create_payment_approval_log(opportunity_name, party_name):
    # Fetch the Lead's lead_name (Opportunity.party_name is linked to Lead)
    lead_name = frappe.db.get_value("Lead", party_name, "lead_name")
    lead_age = frappe.db.get_value("Lead", party_name, "custom_age")
    lead_custom_course_categories = frappe.db.get_value("Lead", party_name, "custom_course_categories")
    lead_custom_board = frappe.db.get_value("Lead", party_name, "custom_board")
    lead_gender = frappe.db.get_value("Lead", party_name, "gender")
    lead_email_id = frappe.db.get_value("Lead", party_name, "email_id")
    lead_class = frappe.db.get_value("Lead", party_name, "custom_class")
    lead_mobile_no = frappe.db.get_value("Lead", party_name, "mobile_no")

    # Create and save Payment Approval Log as Draft
    log = frappe.get_doc({
        "doctype": "Payment Approval Log",
        "lead_reference": party_name,
        "opportunity_reference": opportunity_name,
        "student_name": lead_name,
        "age": lead_age,
        "course_category": lead_custom_course_categories,
        "board": lead_custom_board,
        "gender": lead_gender,
        "email_id": lead_email_id,
        "class": lead_class,
        "mobile_number": lead_mobile_no,
        "date": frappe.utils.today()
    })
    log.insert(ignore_permissions=True)

    # Update Opportunity status directly in DB — avoids making the form dirty
    frappe.db.set_value("Opportunity", opportunity_name, "status", "Payment Approval Pending")
    frappe.db.commit()

    return log.name
