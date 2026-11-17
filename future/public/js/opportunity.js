
frappe.ui.form.on("Opportunity", {
    // Lost / Closed needs the reason typed (required; see opportunity.json property setters).
    status(frm) {
        if (["Lost", "Closed"].includes(frm.doc.status)) {
            setTimeout(() => frm.scroll_to_field("order_lost_reason"), 200);
        }
    },

    refresh(frm) {
        
        calculate_total_amount(frm);
        calculate_total_received_amount(frm);
        calculate_total_amount_vehicle(frm);
        calculate_total_received_amount_vehicle(frm);
        calculate_total_received_amount_pgm(frm)
        calculate_program_total_amount(frm)
    

        // Hide "Customer" from the "Create" group button
        setTimeout(() => {
            frm.remove_custom_button(__("Supplier Quotation"), __("Create"));
            frm.remove_custom_button(__("Request For Quotation"), __("Create"));
            frm.remove_custom_button(__("Quotation"), __("Create"));
            frm.remove_custom_button(__("Customer"), __("Create"));
            // frm.remove_custom_button(__("Add to Prospect"), __("Action"));
        }, 200);




        if (!frm.is_new()) {
            const discount_added = frm.doc.custom_add_discount === 1;
            const discount_approved = frm.doc.custom_discount_approved === 1;

            const show_payment = (discount_approved || !discount_added)
                && frm.doc.status !== "Payment Approval Pending";

            const show_discount = (discount_added && !discount_approved)
                && frm.doc.status !== "Discount Approval Pending";

            if (show_payment) {
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

            if (show_discount) {
                frm.add_custom_button(__("Discount Approval"), function () {
                    frappe.call({
                        method: "future.api_2.create_discount_approval_log",
                        args: {
                            opportunity_name: frm.doc.name,
                            party_name: frm.doc.party_name
                        },
                        callback: function (r) {
                            if (!r.exc) {
                                // Remove the button immediately so it can't be clicked again
                                frm.remove_custom_button(__("Discount Approval"));

                                // Reflect DB status on the form without making it dirty
                                frm.doc.status = "Discount Approval Pending";
                                frm.refresh_field("status");

                                frappe.msgprint({
                                    title: __("Success"),
                                    message: __("Discount Approval Log created successfully"),
                                    indicator: "green"
                                });
                            }
                        }
                    });
                });
            }
        }
    },

    setup(frm) { 
        // Discounts of the chosen type for this programme; the percentage comes from the discount.
        frm.set_query('custom_discount_id', function () {
            return { query: "future.api_2.get_discounts_for_program",
                filters: { base_of_discount: frm.doc.custom_base_of_discount,
                 program: frm.doc.custom_program } };
                });
            },

    custom_base_of_discount(frm) {
        if (frm.doc.custom_merit_based && frm.doc.custom_discount_id) frm.set_value("custom_discount_id", "");
    },
    custom_discount_id(frm) {
        if (!frm.doc.custom_discount_id) {
            frm.set_value({ custom_percentage: "", custom_discount_amount: 0 });
        }
        future_set_fee_after_discount(frm);
    },
    custom_discount_amount: future_set_fee_after_discount,
    custom_special_discount_amount: future_set_fee_after_discount,
    custom_total_amount_gst: future_set_fee_after_discount,
    custom_add_discount: future_set_fee_after_discount,

    // custom_add_discount: function(frm){
    //     if(doc.custom_add_discount===1){
    //         frm.set_value("status", components);

    //     }

    // },




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
    custom_program: function (frm) {
        if (!frm.doc.custom_program) {
            frm.set_value("custom_fees_details", []);
            return;
        }

        frappe.db.get_doc("Program", frm.doc.custom_program)
            .then((doc) => {
                const components = (doc.custom_fees_details || []).map((row) => ({
                    components: row.component,
                    amount: row.amount_with_gst,
                }));
                frm.set_value("custom_fees_details", components);
                calculate_program_total_amount(frm);
            });
    },


    custom_hostel: function (frm) {
        if (!frm.doc.custom_hostel) {
            frm.set_value("custom_hostel_components", []);
            return;
        }

        frappe.db.get_doc("Hostel", frm.doc.custom_hostel)
            .then((doc) => {
                const components = (doc.details || []).map((row) => ({
                    components: row.components,
                    amount: row.amount
                }));
                frm.set_value("custom_hostel_components", components);
                calculate_total_amount(frm);
            });
    },
    custom_vehicle: function(frm){
        if (!frm.doc.custom_vehicle) {
            frm.set_value("custom_vehicle_components", []);
            return;
        }

        frappe.db.get_doc("Vehicle Fee", frm.doc.custom_vehicle)
            .then((doc) => {
                const components = (doc.details || []).map((row) => ({
                    components: row.components,
                    amount: row.amount
                }));
                frm.set_value("custom_vehicle_components", components);
                calculate_total_amount_vehicle(frm);
            });


    },
    custom_received_amount: function (frm) {
        if (frm.doc.custom_received_amount) {

            frm.set_value(
                "custom_balance",
                frm.doc.custom_total_amount - frm.doc.custom_received_amount
            );
        }
    },
    custom_fee_structure: function(frm) {
        if (!frm.doc.custom_fee_structure) {
            frm.set_value("custom_fee_schedule", "");
            return;
        }
    
        frappe.db.get_list("Fee Schedule", {
            filters: {
                fee_structure: frm.doc.custom_fee_structure
            },
            fields: ["name"],
            order_by: "modified desc",
            limit: 1
        }).then((r) => {
            if (r.length) {
                frm.set_value("custom_fee_schedule", r[0].name);
            } else {
                frm.set_value("custom_fee_schedule", "");
                frappe.msgprint(__("No Fee Schedule found for the selected Fee Structure."));
            }
        });
    }
});



frappe.ui.form.on("Hostel Fee Details", {
    amount(frm) {
        calculate_total_amount(frm);
        calculate_total_amount_vehicle(frm);
    },
    custom_hostel_components_remove(frm) {

        calculate_total_amount(frm);
        
        calculate_total_received_amount(frm);
       
        

    },
    custom_fees_details_remove(frm) {
        
        calculate_total_received_amount_pgm(frm)
        calculate_program_total_amount(frm)
    },

    custom_vehicle_components_remove(frm){
            calculate_total_amount_vehicle(frm);
             calculate_total_received_amount_vehicle(frm);
    },


    received_amount: function (frm) {
        calculate_total_received_amount(frm);
        calculate_total_received_amount_vehicle(frm);
        calculate_total_received_amount_pgm(frm)
    }
});

function calculate_total_amount(frm) {
    let total = 0;
    (frm.doc.custom_hostel_components || []).forEach((row) => {
        total += flt(row.amount);
    });
    frm.set_value("custom_hostel_total_amount", total);
}

function calculate_total_received_amount(frm) {
    let total_2 = 0;
    (frm.doc.custom_hostel_components || []).forEach((row) => {
        total_2 += flt(row.received_amount);
    });
    frm.set_value("custom_hostel_received_amount", total_2);
}


function calculate_total_amount_vehicle(frm) {
    let total = 0;
    (frm.doc.custom_vehicle_components || []).forEach((row) => {
        total += flt(row.amount);
    });
    frm.set_value("custom_vehicle_total_amount", total);
}

function calculate_total_received_amount_vehicle(frm) {
    let total_2 = 0;
    (frm.doc.custom_vehicle_components || []).forEach((row) => {
        total_2 += flt(row.received_amount);
    });
    frm.set_value("custom_vehicle_received_amount", total_2);
}

function calculate_program_total_amount(frm) {
    let total = 0;
    (frm.doc.custom_fees_details || []).forEach((row) => {
        total += flt(row.amount);
    });
    frm.set_value("custom_program_total_amount", total);
    // let total_with_gst = total * 1.18;

    // frm.set_value("custom_total_amount_gst", total_with_gst);
}



function calculate_total_received_amount_pgm(frm) {
    let total_2 = 0;
    (frm.doc.custom_fees_details || []).forEach((row) => {
        total_2 += flt(row.received_amount);
    });
    frm.set_value("custom_program_received_amount", total_2);
}




function future_set_fee_after_discount(frm) {
    const discount = frm.doc.custom_merit_based
        ? flt(frm.doc.custom_discount_amount)
        : flt(frm.doc.custom_special_discount_amount);
    const total = flt(frm.doc.custom_total_amount_gst);
    const after = frm.doc.custom_add_discount && total && discount ? Math.max(total - discount, 0) : 0;
    if (flt(frm.doc.custom_fee_after_discount) !== after) frm.set_value("custom_fee_after_discount", after);
}
