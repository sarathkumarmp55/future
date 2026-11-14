
function patch_interaction_composer_role_field() {
    const Composer = frappe.views && frappe.views.InteractionComposer;
    if (!Composer || Composer.prototype.__future_role_field) return;
    Composer.prototype.__future_role_field = true;

    const _get_fields = Composer.prototype.get_fields;
    Composer.prototype.get_fields = function () {
        const fields = _get_fields.call(this);
        const idx = fields.findIndex((f) => f.fieldname === "assigned_to");
        if (idx === -1) {
            return fields;
        }
        fields.splice(idx, 0, {
            label: __("Role"),
            fieldtype: "Select",
            fieldname: "custom_role",
            options: "\nTeam Lead\nLead Manager\nLead User",
            reqd: 1,
            onchange: () => {
                if (this.dialog) {
                    this.dialog.set_value("assigned_to", "");
                }
            },
        });
        return fields;
    };

    const _create_action = Composer.prototype.create_action;
    Composer.prototype.create_action = function () {
        if (!this.dialog.get_value("custom_role")) {
            frappe.msgprint(__("Please select a Role"));
            return;
        }
        return _create_action.call(this);
    };

    const _create_interaction = Composer.prototype.create_interaction;
    Composer.prototype.create_interaction = function (btn, form_values, selected_attachments) {
        const role = this.dialog.get_value("custom_role");
        if (!role) {
            return _create_interaction.call(this, btn, form_values, selected_attachments);
        }
        const assignee = this.dialog.get_value("assigned_to");
        const lead_field = {
            "Lead Manager": "custom_lead_manager_name",
            "Team Lead": "custom_team_leader",
            "Lead User": "custom_lead_user",
        }[role];
        const composer = this;
        const _call = frappe.call;
        frappe.call = function (opts) {
            if (
                opts &&
                opts.method === "frappe.client.insert" &&
                opts.args &&
                opts.args.doc &&
                opts.args.doc.doctype === "ToDo"
            ) {
                opts.args.doc.custom_lead_role = role;
                const _callback = opts.callback;
                opts.callback = async function (r) {
                    if (
                        r &&
                        !r.exc &&
                        assignee &&
                        lead_field &&
                        composer.frm &&
                        composer.frm.docname
                    ) {
                        await frappe.db.set_value(
                            composer.frm.doctype,
                            composer.frm.docname,
                            lead_field,
                            assignee
                        );
                    }
                    return _callback && _callback.apply(this, arguments);
                };
            }
            return _call.apply(this, arguments);
        };
        try {
            return _create_interaction.call(this, btn, form_values, selected_attachments);
        } finally {
            frappe.call = _call;
        }
    };

    const _get_values = Composer.prototype.get_values;
    Composer.prototype.get_values = function () {
        const values = _get_values.call(this);
        if (values) {
            delete values.custom_role;
        }
        return values;
    };

    const _make = Composer.prototype.make;
    Composer.prototype.make = function () {
        _make.call(this);
        const assigned_to = this.dialog.fields_dict.assigned_to;
        if (assigned_to) {
            assigned_to.get_query = () => {
                const role = this.dialog.get_value("custom_role");
                if (role !== "Team Lead" && role !== "Lead Manager") {
                    return;
                }
                return {
                    query: "future.api.get_team_heirarchy_users",
                    filters: { role: role },
                };
            };
        }
    };
}

patch_interaction_composer_role_field();

frappe.ui.form.on("Lead", {
    setup(frm) {
        // Categories offers only the sub-categories of the chosen Course Category.
        frm.set_query("custom_course_sub_category", () => ({
            filters: { course_category: frm.doc.custom_course_categories || "", disabled: 0 },
        }));

        frm.set_query("custom_lead_manager_name", function () {
            return {
                query: "future.api.get_team_heirarchy_users",
                filters: { role: "Lead Manager" },
            };
        });

        frm.set_query("custom_team_leader", function () {
            return {
                query: "future.api.get_team_heirarchy_users",
                filters: { role: "Team Lead" },
            };
        });
    },

    refresh(frm) {
        patch_interaction_composer_role_field();
        // Gender is required when a person fills the form; imports may leave it blank (lead_form_fixes).
        frm.set_df_property("gender", "reqd", 1);

        // Hide "Customer" from the "Create" group button
        setTimeout(() => {
            frm.remove_custom_button(__("Customer"), __("Create"));
            frm.remove_custom_button(__("Prospect"), __("Create"));
            frm.remove_custom_button(__("Quotation"), __("Create"));
            frm.remove_custom_button(__("Add to Prospect"), __("Action"));
            frm.remove_custom_button(__("Opportunity"), __("Create"));

            // Opportunity only after the call connected and the student is interested
            // (same rule is enforced on the server: future.lead_stages.validate_opportunity_from_lead).
            const interested_stage = ["Interested", "Demo Scheduled", "Negotiation", "Opportunity", "Qualified",
                "Manager Approval", "Discount Approval Pending", "Discount Approved", "Payment Approval Pending",
                "Payment Done", "Won", "Converted Student"];
            const ready = frm.doc.custom_connected_status === "Interested" || interested_stage.includes(frm.doc.status);
            if (!frm.is_new() && ready) {
                frm.add_custom_button(__("Opportunity"), function () {
                    frappe.model.open_mapped_doc({
                        method: "erpnext.crm.doctype.lead.lead.make_opportunity",
                        frm: frm,
                    });
                }, __("Create"));
            }
        }, 200);

    },

    custom_course_categories(frm) {
        if (frm.doc.custom_course_sub_category) frm.set_value("custom_course_sub_category", "");
    },

    custom_student_class(frm) {
        // "Other" means the class has to be typed (e.g. Class 4); otherwise Class mirrors Student Class.
        if (frm.doc.custom_student_class === "Other") {
            frm.set_value("custom_class", "");
            setTimeout(() => frm.scroll_to_field("custom_class"), 200);
        } else {
            frm.set_value("custom_class", frm.doc.custom_student_class || "");
        }
    },



    custom_connected_status(frm) {
        if (frm.doc.custom_connected_status === "Interested") {
            frm.set_value("status", "Qualified");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Call Back Requested") {
            frm.set_value("status", "Schedule Callback");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Follow-up Scheduled") {
            frm.set_value("status", "Set Reminder");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Parent Not Available") {
            frm.set_value("status", "Follow-up");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Student Not Available") {
            frm.set_value("status", "Follow-up");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Course Details Shared") {
            frm.set_value("status", "Follow-up");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Fee Details Shared") {
            frm.set_value("status", "Follow-up");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Scholarship Discussion") {
            frm.set_value("status", "Manager Approval");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Demo Class Scheduled") {
            frm.set_value("status", "Opportunity");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Branch Visit Scheduled") {
            frm.set_value("status", "Opportunity");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Payment Pending") {
            frm.set_value("status", "Opportunity");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Admission Confirmed") {
            frm.set_value("status", "Payment Done");
            frm.save();

        }
        if (frm.doc.custom_connected_status === "Not Interested") {
            // No auto-save here: the reason has to be typed first (required for Not Interested).
            frm.set_value("status", "Disqualified");
            setTimeout(() => frm.scroll_to_field("custom_reason"), 200);
        }
        if (frm.doc.custom_connected_status === "") {
            frm.set_value("status", "Lead");
            frm.save();

        }
    },
    custom_call_status(frm) {
        if (frm.doc.custom_call_status === "Wrong Number") {
            frm.set_value("status", "Invalid");
            frm.save();

        }
        if (frm.doc.custom_call_status === "Language Barrier") {
            frm.set_value("status", "Reassign");
            frm.save();

        }
        if (frm.doc.custom_call_status === "Job Enquiry") {
            frm.set_value("status", "Close Lead");
            frm.save();

        }
        if (frm.doc.custom_call_status === "Charity Enquiry") {
            frm.set_value("status", "Close Lead");
            frm.save();

        }
        if (frm.doc.custom_call_status === "Marketing Call") {
            frm.set_value("status", "Close Lead");
            frm.save();

        }
        if (frm.doc.custom_call_status === "Did Not Pick") {
            frm.set_value("status", "Did Not Pick");
            frm.save();

        }
        if (frm.doc.custom_call_status === "Lead Ownership") {
            frm.set_value("status", "Lead");
            frm.save();

        }
        if (frm.doc.custom_call_status === "Disqualified") {
            frm.set_value("status", "Disqualified");
            frm.save();

        }
    }
});

