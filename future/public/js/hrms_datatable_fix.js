// HRMS bulk tools (Shift Assignment Tool, Leave Control Panel, Bulk Salary
// Structure Assignment) reuse one employee DataTable and refresh it whenever
// the filters change. DataTable keeps the row indices from the last inline
// column search in `datamanager._filteredRows` and never clears them on
// refresh, so "select all" afterwards only checks those stale rows.
$(document).on("app_ready", () => {
	if (!window.hrms || !hrms.render_employees_datatable || hrms._future_select_all_fix) {
		return;
	}

	const render_employees_datatable = hrms.render_employees_datatable;

	hrms.render_employees_datatable = function (frm, ...args) {
		const datatable = frm.employees_datatable;

		if (datatable) {
			datatable.datamanager._filteredRows = null;
			$(datatable.header)
				.find(".dt-filter")
				.each((i, input) => (input.value = ""));
		}

		return render_employees_datatable.call(this, frm, ...args);
	};

	hrms._future_select_all_fix = true;
});
