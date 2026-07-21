// Copyright (c) 2026, sarath and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payment Approval Log", {
    mode_of_payment: function (frm) {
        if (frm.doc.mode_of_payment) {
            frappe.db.get_doc("Mode of Payment", frm.doc.mode_of_payment)
                .then((doc) => {
                    if (doc.accounts && doc.accounts.length > 0) {
                        frm.set_value(
                            "account_paid_to",
                            doc.accounts[0].default_account
                        );
                    }
                });
        }
    },
    received_amount: function (frm) {
        if (frm.doc.received_amount) {

            frm.set_value(
                "balance",
                frm.doc.total_amount - frm.doc.received_amount
            );
        }
    }
});
