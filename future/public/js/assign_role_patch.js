// Adds a required Role (Team Lead / Lead Manager / Lead User) to the Assign To dialog and
// records it through future.api.set_lead_assignment_role, which makes the assignment a hand-over.

function patch_assign_to_dialog_role_field() {
    const AssignToDialog = frappe.ui.form && frappe.ui.form.AssignToDialog;
    if (!AssignToDialog || AssignToDialog.prototype.__future_role_field) return;
    AssignToDialog.prototype.__future_role_field = true;

    const _get_fields = AssignToDialog.prototype.get_fields;
    AssignToDialog.prototype.get_fields = function () {
        const fields = _get_fields.call(this);
        const idx = fields.findIndex((f) => f.fieldname === "assign_to");
        if (idx === -1) {
            return fields;
        }
        fields.splice(idx + 1, 0, {
            label: __("Role"),
            fieldtype: "Select",
            fieldname: "custom_role",
            options: "\nTeam Lead\nLead Manager\nLead User",
            reqd: 1,
        });
        return fields;
    };

    const _make = AssignToDialog.prototype.make;
    AssignToDialog.prototype.make = function () {
        _make.call(this);

        const me = this;
        const dialog = this.dialog;
        const _primary_action = dialog.primary_action;

        dialog.set_primary_action(dialog.primary_action_label || __("Add"), function () {
            const role = dialog.get_value("custom_role");
            const assign_to = dialog.get_value("assign_to");
            const _call = frappe.call;

            frappe.call = function (opts) {
                if (opts && opts.method === "frappe.desk.form.assign_to.add_multiple" && opts.args) {
                    const _callback = opts.callback;
                    opts.callback = function (r) {
                        if (r && !r.exc && role && assign_to && assign_to.length) {
                            frappe.xcall("future.api.set_lead_assignment_role", {
                                doctype: me.doctype,
                                names: me.docname,
                                allocated_to: assign_to[0],
                                role: role,
                            });
                        }
                        return _callback && _callback.apply(this, arguments);
                    };
                }
                return _call.apply(this, arguments);
            };

            try {
                return _primary_action.apply(this, arguments);
            } finally {
                frappe.call = _call;
            }
        });
    };
}

patch_assign_to_dialog_role_field();
