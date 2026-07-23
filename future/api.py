# pyrefly: ignore [missing-import]
import frappe

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
        "gender": lead_gender,
        "email_id": lead_email_id,
        "location": opportunity.custom_location,
        "hostel_facility": opportunity.custom_hostel_facility,
        "hostel_type": opportunity.custom_hostel_type,
        "transaction_date": opportunity.custom_payment_date,
        "transaction_id": opportunity.custom_transaction_id,
        "fee_structure": opportunity.custom_fee_structure,
        "received_amount": opportunity.custom_received_amount,
        "program": opportunity.custom_program,
        "academic_year": opportunity.custom_academic_year,
        "total_amount": opportunity.custom_total_amount,
        "mode_of_payment": opportunity.custom_mode_of_payment,
        "account_paid_to": opportunity.custom_account_paid_to,
        "balance": opportunity.custom_balance,

        "class": lead_class,
        "mobile_number": lead_mobile_no,
        "date": frappe.utils.today()
    })

    log.insert(ignore_permissions=True)

    frappe.db.set_value(
        "Opportunity",
        opportunity.name,
        "status",
        "Payment Approval Pending"
    )

    frappe.db.commit()

    return log.name