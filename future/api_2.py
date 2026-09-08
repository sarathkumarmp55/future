# pyrefly: ignore [missing-import]
import frappe

@frappe.whitelist()
def create_discount_approval_log(opportunity_name, party_name):

    opportunity = frappe.get_doc("Opportunity", opportunity_name)
    lead_name = frappe.db.get_value("Lead", party_name, "lead_name")
    # lead_student = frappe.db.get_value("Lead", party_name, "lead_name")
    

    log = frappe.get_doc({
        "doctype": "Discount Approval Log",
        "lead_reference": party_name,
        "opportunity_reference": opportunity.name,
        "discount_id": opportunity.custom_discount_id,
        "lead_name": lead_name,
    })

    
    log.insert(ignore_permissions=True)
    if party_name:
        frappe.db.set_value(
            "Lead",
            party_name,
            "status",
            "Discount Approval Pending"
        )

    frappe.db.set_value(
        "Opportunity",
        opportunity.name,
        "status",
        "Discount Approval Pending"
    )

    frappe.db.commit()

    return log.name



@frappe.whitelist()
def create_discount_approval_log_2(dal, student):

    # dal_id = frappe.get_doc("Student Service", dal)
    dal_doc = frappe.get_doc("Student Service", dal)
    # lead_name = frappe.db.get_value("Lead", party_name, "lead_name")
    # lead_student = frappe.db.get_value("Lead", party_name, "lead_name")
    

    log = frappe.get_doc({
        "doctype": "Discount Approval Log",
        "from_student_service": 1,
        "student": student,
        "discount_id": dal_doc.new_discount_id,
        "student_service":dal_doc.name
    })

    frappe.db.set_value(
        "Student Service",
        dal_doc.name,
        "service_status",
        "Discount Approval Pending"
    )
    log.insert(ignore_permissions=True)
    frappe.db.commit()

    return log.name
