# pyrefly: ignore [missing-import]
import frappe

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_discounts_for_program(doctype, txt, searchfield, start, page_len, filters):
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	filters = filters or {}

	or_filters = []
	if txt:
		or_filters.append(["Discount", "discount_name", "like", f"%{txt}%"])

	conditions = {}
	if filters.get("percentage"):
		conditions["percentage"] = filters.get("percentage")
	if filters.get("base_of_discount"):
		conditions["base_of_discount"] = filters.get("base_of_discount")

	if filters.get("program"):
		discount_names = frappe.db.get_all(
			"Multiselect Program",
			filters={"program": filters.get("program")},
			pluck="parent",
		)
		conditions["name"] = ["in", discount_names or [""]]

	return frappe.get_list(
		"Discount",
		fields=["name", "discount_name"],
		filters=conditions,
		or_filters=or_filters,
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


@frappe.whitelist()
def create_discount_approval_log(opportunity_name, party_name):

    opportunity = frappe.get_doc("Opportunity", opportunity_name)
    lead_name = frappe.db.get_value("Lead", party_name, "lead_name")
    # lead_student = frappe.db.get_value("Lead", party_name, "lead_name")
    
    if opportunity.custom_merit_based == 1:

        log = frappe.get_doc({
            "doctype": "Discount Approval Log",
            "lead_reference": party_name,
            "opportunity_reference": opportunity.name,
            "discount_id": opportunity.custom_discount_id,
            "lead_name": lead_name,
            "from_opportunity": 1,
            "mark": opportunity.custom_mark,
            "score_card": opportunity.custom_score_card,
            "amount": opportunity.custom_discount_amount
        })

        
        log.insert(ignore_permissions=True)

    if opportunity.custom_customer_based == 1:

        log = frappe.get_doc({
            "doctype": "Discount Approval Log",
            "lead_reference": party_name,
            "opportunity_reference": opportunity.name,
            "lead_name": lead_name,
            "from_opportunity": 1,
            "base_of_discount": opportunity.custom_base_of_discount,
            "amount": opportunity.custom_special_discount_amount
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

    existing = frappe.db.exists(
        "Discount Approval Log",
        {"student_service": dal_doc.name, "docstatus": ["<", 2]},
    )
    if existing:
        frappe.throw("Discount Approval Log already created for this Student Service")
    
    if dal_doc.merit_based==1:

        log = frappe.get_doc({
            "doctype": "Discount Approval Log",
            "from_student_service": 1,
            "student": student,
            "discount_id": dal_doc.new_discount_id,
            "student_service":dal_doc.name,
            "mark":dal_doc.mark,
            "score_card": dal_doc.score_card,
            "amount": dal_doc.discount_amount
        })
        log.insert(ignore_permissions=True)

    if dal_doc.customer_based==1:
        log = frappe.get_doc({
            "doctype": "Discount Approval Log",
            "from_student_service": 1,
            "student": student,
            "student_service":dal_doc.name,
            "base_of_discount":dal_doc.base_of_discount,
            "amount": dal_doc.special_discount_amount
        })
        log.insert(ignore_permissions=True)

    frappe.db.set_value(
        "Student Service",
        dal_doc.name,
        "service_status",
        "Discount Approval Pending"
    )
    
    frappe.db.commit()

    return log.name
