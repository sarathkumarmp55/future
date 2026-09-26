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
def get_dashboard_data(filters=None):
    """
    Get Lead dashboard data.

    Default:
        From Date = Today
        To Date   = Today

    Date filtering is based on Lead.creation.
    """

    filters = frappe.parse_json(filters) if filters else {}

    date_filters = _get_date_filters(filters)
    conditions = _build_conditions(filters, date_filters)

    kpis = _get_kpis(conditions)
    gender = _get_gender_counts(conditions)
    sources = _get_sources(conditions)
    statuses = _get_status_counts(conditions)

    return {
        "date_filters": date_filters,
        "kpis": kpis,
        "gender": gender,
        "sources": sources,
        "statuses": statuses
    }


# =========================================================
# DATE FILTER
# =========================================================

def _get_date_filters(filters):
    """
    Default date:
        From Date = Today
        To Date   = Today

    Date is applied against Lead.creation.
    """

    today = frappe.utils.today()

    from_date = filters.get("from_date") or today
    to_date = filters.get("to_date") or today

    return {
        "from_date": from_date,
        "to_date": to_date
    }


# =========================================================
# BUILD CONDITIONS
# =========================================================

def _build_conditions(filters, date_filters):
    """
    Build common Lead conditions.

    Date filter is applied using Lead.creation.
    """

    conditions = ["1 = 1"]

    # -----------------------------------------------------
    # Creation Date
    # -----------------------------------------------------

    if date_filters.get("from_date"):
        from_date = frappe.utils.getdate(
            date_filters["from_date"]
        )

        conditions.append(
            f"l.creation >= '{from_date} 00:00:00'"
        )

    if date_filters.get("to_date"):
        to_date = frappe.utils.getdate(
            date_filters["to_date"]
        )

        conditions.append(
            f"l.creation <= '{to_date} 23:59:59'"
        )

    # -----------------------------------------------------
    # Course Category
    # -----------------------------------------------------

    if filters.get("course_category"):
        conditions.append(
            "l.custom_course_categories = "
            + frappe.db.escape(
                filters["course_category"]
            )
        )

    # -----------------------------------------------------
    # Source
    # -----------------------------------------------------

    if filters.get("source"):
        conditions.append(
            "l.source = "
            + frappe.db.escape(
                filters["source"]
            )
        )

    # -----------------------------------------------------
    # Location
    # -----------------------------------------------------

    if filters.get("location"):
        location = filters["location"]

        location_value = frappe.db.escape(
            f"%{location}%"
        )

        conditions.append(
            f"""
            (
                l.custom_location LIKE {location_value}
                OR l.city LIKE {location_value}
                OR l.territory LIKE {location_value}
            )
            """
        )

    # -----------------------------------------------------
    # Status
    # -----------------------------------------------------

    if filters.get("status_filter"):
        conditions.append(
            "l.status = "
            + frappe.db.escape(
                filters["status_filter"]
            )
        )

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------

    if filters.get("search"):
        search = filters["search"]

        search_value = frappe.db.escape(
            f"%{search}%"
        )

        conditions.append(
            f"""
            (
                l.lead_name LIKE {search_value}
                OR l.mobile_no LIKE {search_value}
                OR l.phone LIKE {search_value}
                OR l.email_id LIKE {search_value}
            )
            """
        )

    return " AND ".join(conditions)


# =========================================================
# KPI
# =========================================================

def _get_kpis(conditions):

    # Total Leads
    total = _count(conditions)

    # New Leads
    new_leads = _count(
        f"""
        {conditions}
        AND l.status = 'Lead'
        """
    )

    # Contacted
    contacted = _count(
        f"""
        {conditions}
        AND l.status = 'Contacted'
        """
    )

    # Interested
    interested = _count(
        f"""
        {conditions}
        AND l.status IN ('Opportunity', 'Qualified')
        """
    )

    # Counselled
    counselled = _count(
        f"""
        {conditions}
        AND l.status IN ('Opportunity', 'Qualified')
        """
    )

    # Admissions
    admissions = _count(
        f"""
        {conditions}
        AND l.status = 'Converted Student'
        """
    )

    # Conversion Rate
    conversion_rate = (
        round(
            (admissions / total) * 100,
            2
        )
        if total
        else 0
    )

    return {
        "total": total,
        "new_leads": new_leads,
        "contacted": contacted,
        "interested": interested,
        "counselled": counselled,
        "admissions": admissions,
        "conversion_rate": conversion_rate
    }


# =========================================================
# GENDER
# =========================================================

def _get_gender_counts(conditions):

    return frappe.db.sql(
        f"""
        SELECT
            COALESCE(
                NULLIF(l.gender, ''),
                'Unknown'
            ) AS gender,

            COUNT(*) AS total_count

        FROM `tabLead` l

        WHERE {conditions}

        GROUP BY
            COALESCE(
                NULLIF(l.gender, ''),
                'Unknown'
            )

        ORDER BY total_count DESC
        """,
        as_dict=True
    )


# =========================================================
# SOURCE
# =========================================================

def _get_sources(conditions):

    return frappe.db.sql(
        f"""
        SELECT
            COALESCE(
                NULLIF(l.source, ''),
                'Unknown'
            ) AS source,

            COUNT(*) AS total_count

        FROM `tabLead` l

        WHERE {conditions}

        GROUP BY
            COALESCE(
                NULLIF(l.source, ''),
                'Unknown'
            )

        ORDER BY total_count DESC
        """,
        as_dict=True
    )


# =========================================================
# STATUS
# =========================================================

def _get_status_counts(conditions):

    return frappe.db.sql(
        f"""
        SELECT
            COALESCE(
                NULLIF(l.status, ''),
                'Unknown'
            ) AS status,

            COUNT(*) AS total_count

        FROM `tabLead` l

        WHERE {conditions}

        GROUP BY
            COALESCE(
                NULLIF(l.status, ''),
                'Unknown'
            )

        ORDER BY total_count DESC
        """,
        as_dict=True
    )


# =========================================================
# COUNT
# =========================================================

def _count(conditions):

    result = frappe.db.sql(
        f"""
        SELECT COUNT(*)
        FROM `tabLead` l
        WHERE {conditions}
        """
    )

    return result[0][0] if result else 0


# =========================================================
# PAYMENT APPROVAL LOG DASHBOARD
# =========================================================

@frappe.whitelist()
def get_payment_approval_dashboard_data(filters=None):
    """
    Get Payment Approval Log dashboard data.

    Date filtering is based on Payment Approval Log.date.
    """

    filters = frappe.parse_json(filters) if filters else {}

    date_filters = _get_pal_date_filters(filters)
    conditions = _build_pal_conditions(filters, date_filters)

    kpis = _get_pal_kpis(conditions)
    sources = _get_pal_sources(conditions)
    statuses = _get_pal_status_counts(conditions)

    return {
        "date_filters": date_filters,
        "kpis": kpis,
        "sources": sources,
        "statuses": statuses
    }


# =========================================================
# DATE FILTER
# =========================================================

def _get_pal_date_filters(filters):

    today = frappe.utils.today()

    from_date = filters.get("from_date") or today
    to_date = filters.get("to_date") or today

    return {
        "from_date": from_date,
        "to_date": to_date
    }


# =========================================================
# BUILD CONDITIONS
# =========================================================

def _build_pal_conditions(filters, date_filters):

    conditions = ["1 = 1"]

    # -----------------------------------------------------
    # Date
    # -----------------------------------------------------

    if date_filters.get("from_date"):
        from_date = frappe.utils.getdate(
            date_filters["from_date"]
        )

        conditions.append(
            f"p.date >= '{from_date} 00:00:00'"
        )

    if date_filters.get("to_date"):
        to_date = frappe.utils.getdate(
            date_filters["to_date"]
        )

        conditions.append(
            f"p.date <= '{to_date} 23:59:59'"
        )

    # -----------------------------------------------------
    # Payment Status
    # -----------------------------------------------------

    if filters.get("payment_status"):
        conditions.append(
            "p.payment_status = "
            + frappe.db.escape(
                filters["payment_status"]
            )
        )

    return " AND ".join(conditions)


# =========================================================
# KPI
# =========================================================

def _get_pal_kpis(conditions):

    total = _pal_count(conditions)

    pending = _pal_count(
        f"""
        {conditions}
        AND p.payment_status = 'Pending'
        """
    )

    approved = _pal_count(
        f"""
        {conditions}
        AND p.payment_status = 'Approved'
        """
    )

    rejected = _pal_count(
        f"""
        {conditions}
        AND p.payment_status = 'Rejected'
        """
    )

    from_opportunity = _pal_count(
        f"""
        {conditions}
        AND p.from_opportunity = 1
        """
    )

    from_student_service = _pal_count(
        f"""
        {conditions}
        AND p.from_student_service = 1
        """
    )

    total_bill_amount = _pal_sum(
        "COALESCE(p.total_bill_amount, 0)",
        conditions
    )

    fees_amount = _pal_sum(
        "COALESCE(p.fees_received_amount, 0)",
        conditions
    )

    hostel_amount = _pal_sum(
        "COALESCE(p.hostel_received_amount, 0)",
        conditions
    )

    vehicle_amount = _pal_sum(
        "COALESCE(p.vehicle_received_amount, 0)",
        conditions
    )

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "from_opportunity": from_opportunity,
        "from_student_service": from_student_service,
        "total_bill_amount": total_bill_amount,
        "fees_amount": fees_amount,
        "hostel_amount": hostel_amount,
        "vehicle_amount": vehicle_amount
    }


# =========================================================
# GENDER
# =========================================================

# =========================================================
# SOURCE (Opportunity vs Student Service)
# =========================================================

def _get_pal_sources(conditions):

    return frappe.db.sql(
        f"""
        SELECT
            CASE
                WHEN p.from_opportunity = 1
                    THEN 'Opportunity'
                WHEN p.from_student_service = 1
                    THEN 'Student Service'
                ELSE 'Unknown'
            END AS source,

            COUNT(*) AS total_count

        FROM `tabPayment Approval Log` p

        WHERE {conditions}

        GROUP BY
            CASE
                WHEN p.from_opportunity = 1
                    THEN 'Opportunity'
                WHEN p.from_student_service = 1
                    THEN 'Student Service'
                ELSE 'Unknown'
            END

        ORDER BY total_count DESC
        """,
        as_dict=True
    )


# =========================================================
# STATUS
# =========================================================

def _get_pal_status_counts(conditions):

    return frappe.db.sql(
        f"""
        SELECT
            COALESCE(
                NULLIF(p.payment_status, ''),
                'Unknown'
            ) AS status,

            COUNT(*) AS total_count

        FROM `tabPayment Approval Log` p

        WHERE {conditions}

        GROUP BY
            COALESCE(
                NULLIF(p.payment_status, ''),
                'Unknown'
            )

        ORDER BY total_count DESC
        """,
        as_dict=True
    )


# =========================================================
# COUNT / SUM HELPERS
# =========================================================

def _pal_count(conditions):

    result = frappe.db.sql(
        f"""
        SELECT COUNT(*)
        FROM `tabPayment Approval Log` p
        WHERE {conditions}
        """
    )

    return result[0][0] if result else 0


def _pal_sum(column, conditions):

    result = frappe.db.sql(
        f"""
        SELECT SUM({column})
        FROM `tabPayment Approval Log` p
        WHERE {conditions}
        """
    )

    return flt(result[0][0]) if result and result[0][0] else 0


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