
frappe.ui.form.on("Program", {
    refresh(frm) {
        calculate_total_amount(frm);
    }
});

frappe.ui.form.on("Program Components", {
    amount(frm) {
        calculate_total_amount(frm);
    },
    custom_fees_details_remove(frm) {
        calculate_total_amount(frm);
    },
    amount_with_gst(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        let amount = flt(row.amount_with_gst) / 1.18;

        frappe.model.set_value(cdt, cdn, "amount", amount);

        calculate_total_amount(frm);
    }
});

function calculate_total_amount(frm) {
    let total = 0;
    (frm.doc.custom_fees_details || []).forEach((row) => {
        total += flt(row.amount);
    });
    frm.set_value("custom_total_amount", total);
}
