// Copyright (c) 2026, sarath and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Service", {
	refresh(frm) {

        calculate_total_amount(frm);
        calculate_total_received_amount(frm);
        calculate_total_amount_vehicle(frm);
        calculate_total_received_amount_vehicle(frm);
        calculate_total_received_amount_pgm(frm)
        calculate_program_total_amount(frm)
        refresh_calculation(frm)

        frm.set_query("program", function () {
            return { filters: { name: frm.doc.selected_program } };
        });

        frm.set_query("hostel", function () {
            if (frm.doc.selected_hosted) {
                return {
                    filters: {
                        name: frm.doc.selected_hosted
                    }
                };
            }

            return {};
        });
        frm.set_query("vehicle", function () {
            if (frm.doc.selected_vehicle) {
                return {
                    filters: {
                        name: frm.doc.selected_vehicle
                    }
                };
            }

            return {};
        });


        if (!frm.is_new() && frm.doc.add_discount === 1 && frm.doc.service_status === "Approval Pending") {
                frm.add_custom_button(__("Discount Approval"), function () {
                    frappe.call({
                        method: "future.api_2.create_discount_approval_log_2",
                        args: {
                            dal: frm.doc.name,
                            student: frm.doc.student
                        },
                        callback: function (r) {
                            if (!r.exc) {
                                // Remove the button immediately so it can't be clicked again
                                frm.remove_custom_button(__("Discount Approval"));

                                // Reflect DB status on the form without making it dirty
                                frm.doc.service_status = "Discount Approval Pending";
                                frm.refresh_field("service_status");

                                frappe.msgprint({
                                    title: __("Success"),
                                    message: __("Discount Approval Log created successfully"),
                                    indicator: "green"
                                });
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }

        if (frm.doc.docstatus === 0 && frm.doc.add_discount === 1 && !frm.doc.approved && !frm.doc.__unsaved) {
            frm.page.clear_primary_action();
        }



	},
     setup(frm) { 
        frm.set_query('new_discount_id', function () { 
            return { filters: { percentage: frm.doc.percentage, 
                base_of_discount: frm.doc.base_of_discount,
                 program: frm.doc.program } }; 
                }); 
            },

       program: function (frm) {
        if (!frm.doc.program) {
            frm.set_value("fees_components", []);
            return;
        }

        frappe.db.get_doc("Program", frm.doc.program)
            .then((doc) => {
                const components = (doc.custom_fees_details || []).map((row) => ({
                    components: row.component,
                    amount: row.amount_with_gst
                }));
                console.log(components)
                frm.set_value("fees_components", components);
                calculate_program_total_amount(frm);
                refresh_calculation(frm);
            });
    },


    hostel: function (frm) {
        if (!frm.doc.hostel) {
            frm.set_value("hostel_components", []);
            return;
        }

        frappe.db.get_doc("Hostel", frm.doc.hostel)
            .then((doc) => {
                const components = (doc.details || []).map((row) => ({
                    components: row.components,
                    amount: row.amount
                }));
                console.log(components)
                frm.set_value("hostel_components", components);
                calculate_total_amount(frm);
            });
    },
    vehicle: function(frm){
        if (!frm.doc.vehicle) {
            frm.set_value("vehicle_components", []);
            return;
        }

        frappe.db.get_doc("Vehicle Fee", frm.doc.vehicle)
            .then((doc) => {
                const components = (doc.details || []).map((row) => ({
                    components: row.components,
                    amount: row.amount
                }));
                frm.set_value("vehicle_components", components);
                calculate_total_amount_vehicle(frm);
            });


    },
     mode_of_payement: function (frm) {
        if (frm.doc.mode_of_payement) {
            frappe.db.get_doc("Mode of Payment", frm.doc.mode_of_payement)
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

    hostel_received_amount: function (frm){
        if (frm.doc.selected_hosted) {
            frm.set_value("outstanding_amount_1", frm.doc.hostel_balance_amount - frm.doc.hostel_received_amount);
        }
       
    },
    vehicle_received_amount: function (frm){
        if (frm.doc.selected_vehicle) {
            frm.set_value("outstanding_amount_2", frm.doc.vehicle_balance_amount - frm.doc.vehicle_received_amount);
        }
    },
    received_amount: function (frm) {
        refresh_calculation(frm);
    }




});






frappe.ui.form.on("Hostel Fee Details", {
    amount(frm) {
        calculate_total_amount(frm);
        calculate_total_amount_vehicle(frm);
    },
    hostel_components_remove(frm) {

        calculate_total_amount(frm);
        
        calculate_total_received_amount(frm);
       
        

    },
    fees_components_remove(frm) {
        
        calculate_total_received_amount_pgm(frm)
        calculate_program_total_amount(frm)
        refresh_calculation(frm)
    },

    vehicle_components_remove(frm){
            calculate_total_amount_vehicle(frm);
             calculate_total_received_amount_vehicle(frm);
    },


    received_amount: function (frm) {
        calculate_total_received_amount(frm);
        calculate_total_received_amount_vehicle(frm);
        calculate_total_received_amount_pgm(frm);
        refresh_calculation(frm);
    }
});

function refresh_calculation(frm) {
    if (frm.__refreshing_calculation) return;
    frm.__refreshing_calculation = true;

    if (frm.doc.selected_program) {
        frm.doc.program_total_amount = frm.doc.total_amount;
        frm.refresh_field("program_total_amount");
        let program_balance = flt(frm.doc.program_total_amount) - flt(frm.doc.program_total_received_amount);
        frm.doc.program_balance_amount = program_balance;
        frm.refresh_field("program_balance_amount");
        frm.doc.outstanding_amount = program_balance - flt(frm.doc.received_amount);
        frm.refresh_field("outstanding_amount");
    }

    frm.__refreshing_calculation = false;
}

function calculate_total_amount(frm) {
    let total = 0;
    (frm.doc.hostel_components || []).forEach((row) => {
        total += flt(row.amount);
    });
    frm.doc.hostel_total_amount = total;
    frm.refresh_field("hostel_total_amount");
}

function calculate_total_received_amount(frm) {
    let total_2 = 0;
    (frm.doc.hostel_components || []).forEach((row) => {
        total_2 += flt(row.received_amount);
    });
    frm.doc.hostel_received_amount = total_2;
    frm.refresh_field("hostel_received_amount");
}


function calculate_total_amount_vehicle(frm) {
    let total = 0;
    (frm.doc.vehicle_components || []).forEach((row) => {
        total += flt(row.amount);
    });
    frm.doc.vehicle_total_amount = total;
    frm.refresh_field("vehicle_total_amount");
}

function calculate_total_received_amount_vehicle(frm) {
    let total_2 = 0;
    (frm.doc.vehicle_components || []).forEach((row) => {
        total_2 += flt(row.received_amount);
    });
    frm.doc.vehicle_received_amount = total_2;
    frm.refresh_field("vehicle_received_amount");
}

function calculate_program_total_amount(frm) {
    let total = 0;
    (frm.doc.fees_components || []).forEach((row) => {
        total += flt(row.amount);
    });
    frm.doc.total_amount = total;
    frm.refresh_field("total_amount");
}

function calculate_total_received_amount_pgm(frm) {
    let total_2 = 0;
    (frm.doc.fees_components || []).forEach((row) => {
        total_2 += flt(row.received_amount);
    });
    frm.doc.received_amount = total_2;
    frm.refresh_field("received_amount");
}


