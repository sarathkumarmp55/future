app_name = "future"
app_title = "Future"
app_publisher = "sarath"
app_description = "future"
app_email = "sarath@gmail.com"
app_license = "mit"


# fixtures = [
#     {
#         "dt": "Property Setter",
#         "filters": [
#             ["name", "in", (
#                 "Lead-status-options",
#             )]
#         ]
#     }
# ]





# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "future",
# 		"logo": "/assets/future/logo.png",
# 		"title": "future",
# 		"route": "/future",
# 		"has_permission": "future.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/future/css/future.css"
# app_include_js = "/assets/future/js/future.js"

# include js, css files in header of web template
# web_include_css = "/assets/future/css/future.css"
# web_include_js = "/assets/future/js/future.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "future/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Document Events
# ---------------
doc_events = {
    "Program Enrollment": {
        "validate": "future.admissions.enrollment_validate",
        "on_submit": "future.hostel_management.on_enrollment_change",
        "on_cancel": "future.hostel_management.on_enrollment_change",
        "on_update_after_submit": [
            "future.admissions.enrollment_after_submit_update",
            "future.hostel_management.on_enrollment_change",
        ],
    },
    "Payment Approval Log": {
        "on_submit": "future.admissions.on_pal_submit",
        "on_cancel": "future.admissions.on_pal_cancel",
    },
    "ToDo": {
        "validate": "future.lead_management.validate_todo_assignment",
        "after_insert": "future.lead_management.on_todo_insert",
    },
    "Lead": {
        "validate": "future.events.lead.validate_mobile_no_unique",
        "on_update": [
            "future.events.lead.on_update",
            "future.lead_management.on_lead_update",
        ],
    }
}

# Permission Query Conditions
# ---------------------------
# Salespeople compete, so Leads and Opportunities are private to the people
# working them and their managers. See future/permissions/visibility.py.
permission_query_conditions = {
    "Lead": "future.permissions.visibility.lead_query_conditions",
    "Opportunity": "future.permissions.visibility.opportunity_query_conditions",
    "Contact": "future.permissions.visibility.contact_query_conditions",
    "Address": "future.permissions.visibility.address_query_conditions",
    "Lead Handover": "future.permissions.visibility.handover_query_conditions",
    "Discount Approval Log": "future.permissions.visibility.discount_log_query_conditions",
    "Fee Refund Request": "future.permissions.visibility.refund_query_conditions",
    "Fee Transfer Request": "future.permissions.visibility.transfer_query_conditions",
}

has_permission = {
    "Lead": "future.permissions.visibility.lead_has_permission",
    "Opportunity": "future.permissions.visibility.opportunity_has_permission",
    "Contact": "future.permissions.visibility.contact_has_permission",
    "Address": "future.permissions.visibility.address_has_permission",
    "Lead Handover": "future.permissions.visibility.handover_has_permission",
    "Discount Approval Log": "future.permissions.visibility.owner_has_permission",
    "Fee Refund Request": "future.permissions.visibility.owner_has_permission",
    "Fee Transfer Request": "future.permissions.visibility.owner_has_permission",
}

scheduler_events = {
    "hourly": ["future.lead_management.check_first_call_sla"],
    "daily": [
        "future.lead_management.send_daily_digest",
        "future.hostel_management.refresh_all_occupancy",
        "future.admissions.refresh_overdue",
    ],
}

add_to_apps_screen = [
    {
        "name": app_name,
        "logo": "/assets/future/images/future-logo.svg",
        "title": app_title,
        "route": "/desk/lead-dashboard",
    },
    {
        "name": app_name,
        "logo": "/assets/future/images/hostel-logo.svg",
        "title": "Hostels",
        "route": "/desk/hostel-dashboard",
        "has_permission": "future.hostel_management.can_open_hostels",
    },
]

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "future/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "future.utils.jinja_methods",
# 	"filters": "future.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "future.install.before_install"
# after_install = "future.install.after_install"

after_migrate = ["future.setup.workspace.hide_unused_workspaces"]

# Uninstallation
# ------------

# before_uninstall = "future.uninstall.before_uninstall"
# after_uninstall = "future.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "future.utils.before_app_install"
# after_app_install = "future.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "future.utils.before_app_uninstall"
# after_app_uninstall = "future.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "future.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }


doctype_js = {
    
    "Lead" : ["public/js/lead.js", "public/js/lead_handover_form.js", "public/js/assign_role_patch.js"],
    "Opportunity" : "public/js/opportunity.js",
    "Payment Entry" : "public/js/payment_entry.js",
    "Program" : "public/js/program.js",
    "Program Enrollment" : "public/js/program_enrollment.js",
    "Student" : "public/js/student.js",
    
}

doctype_list_js = {
    "Lead" : ["public/js/list_tiles.js", "public/js/lead_list.js", "public/js/lead_handover_list.js", "public/js/assign_role_patch.js"],
    "Opportunity" : ["public/js/list_tiles.js", "public/js/opportunity_list.js"],
    "Program Enrollment" : ["public/js/list_tiles.js", "public/js/program_enrollment_list.js"],
    "Discount Approval Log" : ["public/js/list_tiles.js", "public/js/money_lists.js"],
    "Fee Refund Request" : ["public/js/list_tiles.js", "public/js/money_lists.js"],
    "Fee Transfer Request" : ["public/js/list_tiles.js", "public/js/money_lists.js"],
    "Payment Approval Log" : ["public/js/list_tiles.js", "public/js/payment_approval_log_list.js"],
    "ToDo" : ["public/js/list_tiles.js", "public/js/followup_lists.js"],
    "Lead Handover" : ["public/js/list_tiles.js", "public/js/followup_lists.js", "public/js/lead_handover_list_status.js"],
}





# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"future.tasks.all"
# 	],
# 	"daily": [
# 		"future.tasks.daily"
# 	],
# 	"hourly": [
# 		"future.tasks.hourly"
# 	],
# 	"weekly": [
# 		"future.tasks.weekly"
# 	],
# 	"monthly": [
# 		"future.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "future.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "future.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "future.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["future.utils.before_request"]
# after_request = ["future.utils.after_request"]

# Job Events
# ----------
# before_job = ["future.utils.before_job"]
# after_job = ["future.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"future.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

