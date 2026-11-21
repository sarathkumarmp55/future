frappe.ui.form.on("Consultant Fee Run", {
	setup(frm) {
		if (frm.is_new() && !frm.doc.company) frm.set_value("company", frappe.defaults.get_default("company"));
	},
	refresh(frm) {
		if (frm.doc.docstatus !== 0) return;
		frm.add_custom_button(__("Get Consultants"), () => {
			if (!frm.doc.fee_month) return frappe.msgprint(__("Choose the fee month first."));
			frm.call("get_consultants").then(() => {
				frm.refresh_fields();
				frm.dirty();
			});
		});
		frm.add_custom_button(__("Create Suppliers"), () => frm.events.create_suppliers(frm));
		frm.set_intro(
			__("Save to work out the fees from attendance. Submit to create a draft Purchase Invoice for each consultant."),
			"blue"
		);
	},
	create_suppliers(frm) {
		const method = "future.hr.payroll_setup.setup_consultants";
		frappe.call({ method, args: { dry_run: 1 }, freeze: true }).then((r) => {
			const log = (r.message && r.message.log) || [];
			const to_create = log.filter((line) => line.startsWith("Supplier for "));
			const notes = log.filter((line) => !line.startsWith("Supplier for "));
			const list = (lines) => lines.map((line) => `<li>${frappe.utils.escape_html(line)}</li>`).join("");
			if (!to_create.length) {
				frappe.msgprint({
					title: __("Create Suppliers"),
					message: __("Every active consultant already has a Supplier.") + (notes.length ? `<ul>${list(notes)}</ul>` : ""),
				});
				return;
			}
			frappe.confirm(
				__("Create a Supplier for these {0} consultant(s) and link it on the Employee?", [to_create.length]) +
					`<ul>${list(to_create)}</ul>` +
					(notes.length ? `<ul class="text-warning">${list(notes)}</ul>` : ""),
				() =>
					frappe.call({ method, args: { dry_run: 0 }, freeze: true }).then(() => {
						frappe.show_alert({ message: __("{0} Supplier(s) created", [to_create.length]), indicator: "green" });
						// saving picks up the new suppliers on the rows
						if (!frm.is_new() && frm.doc.items && frm.doc.items.length) frm.save();
					})
			);
		});
	},
});

frappe.ui.form.on("Consultant Fee Run Item", {
	off_days(frm) {
		// Figures are worked out on the server; saving shows the new fee.
		frm.dirty();
	},
});
