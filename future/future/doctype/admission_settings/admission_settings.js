// Admission Settings: "Import Masters from Excel" (centres, hostels, program prices, price chart).
// Always shows a dry run first; nothing is saved until the second confirmation.
const IMPORT_METHOD = "future.setup.import_masters.import_from_file";

frappe.ui.form.on("Admission Settings", {
	refresh(frm) {
		if (!frappe.user.has_role("System Manager")) return;
		frm.add_custom_button(__("Import Masters from Excel"), () => {
			new frappe.ui.FileUploader({
				restrictions: { allowed_file_types: [".xlsx"] },
				folder: "Home/Attachments",
				on_success(file) {
					frappe
						.xcall(IMPORT_METHOD, { file_url: file.file_url, dry_run: 1 })
						.then((r) => confirm_import(frm, file.file_url, r));
				},
			});
		});
	},
});

function report_html(r) {
	const s = r.summary;
	const esc = frappe.utils.escape_html;
	const lines = r.log.filter((l) => !l.startsWith("DRY RUN"));
	return `
		<p>${__("After the import the site will have {0} centres, {1} hostels and {2} programmes ({3} with a price split).", [
			s.centers, s.hostels, s.programs, s.programs_priced,
		])}</p>
		${lines.length ? `<ul style="max-height:280px;overflow:auto;padding-left:18px">${lines.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : `<p>${__("Everything already matches the workbook; existing records will be refreshed.")}</p>`}`;
}

function confirm_import(frm, file_url, dry) {
	frappe.confirm(
		`<p><b>${__("Dry run: nothing has been saved yet.")}</b></p>${report_html(dry)}<p>${__("Import now?")}</p>`,
		() =>
			frappe.xcall(IMPORT_METHOD, { file_url, dry_run: 0 }).then((r) => {
				frappe.msgprint({ title: __("Masters imported"), message: report_html(r), indicator: "green" });
				frm.reload_doc();
			})
	);
}
