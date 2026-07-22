
frappe.ui.form.on("Opportunity", {
    refresh(frm) {

        // Hide "Customer" from the "Create" group button
        setTimeout(() => {
            frm.remove_custom_button(__("Supplier Quotation"), __("Create"));
            frm.remove_custom_button(__("Request For Quotation"), __("Create"));
            frm.remove_custom_button(__("Quotation"), __("Create"));
            frm.remove_custom_button(__("Customer"), __("Create"));
            // frm.remove_custom_button(__("Add to Prospect"), __("Action"));
        }, 200);




        // Only show the button if a Payment Approval Log hasn't been created yet
        if (!frm.is_new()) {
            if (frm.doc.status !== "Payment Approval Pending") {
                frm.add_custom_button(__("Payment Approval"), function () {
                    frappe.call({
                        method: "future.api.create_payment_approval_log",
                        args: {
                            opportunity_name: frm.doc.name,
                            party_name: frm.doc.party_name
                        },
                        callback: function (r) {
                            if (!r.exc) {
                                // Remove the button immediately so it can't be clicked again
                                frm.remove_custom_button(__("Payment Approval"));

                                // Reflect DB status on the form without making it dirty
                                frm.doc.status = "Payment Approval Pending";
                                frm.refresh_field("status");

                                frappe.msgprint({
                                    title: __("Success"),
                                    message: __("Payment Approval Log created successfully"),
                                    indicator: "green"
                                });
                            }
                        }
                    });
                });
            }
        }
    },
    custom_mode_of_payment: function (frm) {
        if (frm.doc.custom_mode_of_payment) {
            frappe.db.get_doc("Mode of Payment", frm.doc.custom_mode_of_payment)
                .then((doc) => {
                    if (doc.accounts && doc.accounts.length > 0) {
                        frm.set_value(
                            "custom_account_paid_to",
                            doc.accounts[0].default_account
                        );
                    }
                });
        }
    },
    custom_received_amount: function (frm) {
        if (frm.doc.custom_received_amount) {

            frm.set_value(
                "custom_balance",
                frm.doc.custom_total_amount - frm.doc.custom_received_amount
            );
        }
    },
});
