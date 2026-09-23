// Copyright (c) 2026, sarath and contributors
// For license information, please see license.txt

frappe.ui.form.on("App Access Approval Log", {
	refresh(frm) {
		load_pending_students(frm);
		add_bulk_provide_button(frm);
	}
});

frappe.ui.form.on("App Access", {
	app_access_provide(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (!row.student) {
			frappe.msgprint(__("Student is required"));
			return;
		}

		prompt_transaction_id((transaction_id) => {
			frappe.call({
				method: "future.api.provide_app_access",
				args: {
					student: row.student,
					transaction_id: transaction_id
				},
				freeze: true,
				freeze_message: __("Providing app access..."),
				callback: function (r) {
					if (r.exc) {
						show_access_error();
						return;
					}

					const grid = frm.get_field("table_czqr").grid;
					const grid_row = grid.grid_rows_by_docname[cdn];
					if (grid_row) {
						grid_row.remove();
					}

					frappe.show_alert({
						message: __("App access provided for {0}", [row.student_name || row.student]),
						indicator: "green"
					});
				}
			});
		});
	}
});

function add_bulk_provide_button(frm) {
	frm.remove_custom_button(__("Provide Access to Selected"));
	frm.add_custom_button(__("Provide Access to Selected"), () => {
		const grid = frm.get_field("table_czqr").grid;
		const selected = grid.get_selected_children();

		if (!selected.length) {
			frappe.msgprint(__("Select at least one student"));
			return;
		}

		const students = selected.map((row) => row.student).filter(Boolean);

		if (!students.length) {
			frappe.msgprint(__("Selected rows have no student"));
			return;
		}

		prompt_transaction_id((transaction_id) => {
			frappe.call({
				method: "future.api.provide_app_access_bulk",
				args: {
					students: students,
					transaction_id: transaction_id
				},
				freeze: true,
				freeze_message: __("Providing app access..."),
				callback: function (r) {
					if (r.exc) {
						show_access_error();
						return;
					}

					frappe.show_alert({
						message: __("App access provided for {0} students", [students.length]),
						indicator: "green"
					});

					load_pending_students(frm);
				}
			});
		});
	});
}

function prompt_transaction_id(callback) {
	const dialog = new frappe.ui.Dialog({
		title: __("App Access Transaction ID"),
		fields: [
			{
				fieldname: "transaction_id",
				fieldtype: "Data",
				label: __("Access ID"),
				reqd: 1
			}
		],
		primary_action_label: __("Provide Access"),
		primary_action(values) {
			if (!values.transaction_id) {
				frappe.msgprint(__("Please enter the Access ID"));
				return;
			}

			dialog.hide();
			callback(values.transaction_id);
		}
	});

	dialog.show();
}

function show_access_error() {
	frappe.msgprint({
		title: __("Error"),
		indicator: "red",
		message: __("Could not provide app access. Please try again.")
	});
}

function load_pending_students(frm) {
	frappe.call({
		method: "future.api.get_students_without_app_access",
		callback: function (r) {
			if (r.exc) {
				return;
			}

			frm.clear_table("table_czqr");

			(r.message || []).forEach((student) => {
				frm.add_child("table_czqr", {
					student: student.name,
					student_name: student.student_name || student.first_name
				});
			});

			frm.refresh_field("table_czqr");
		}
	});
}
