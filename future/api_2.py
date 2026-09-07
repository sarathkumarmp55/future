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
