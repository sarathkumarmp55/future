// Payments Dashboard: what came in, what is waiting on me, and who still owes.
frappe.pages["payments-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Payments Dashboard"), single_column: true });
	frappe.require("/assets/future/js/future_dash.js", () => {
		wrapper.payments_dashboard = new PaymentsDashboard(page);
	});
};

frappe.pages["payments-dashboard"].on_page_show = function (wrapper) {
	wrapper.payments_dashboard && wrapper.payments_dashboard.refresh();
};

class PaymentsDashboard {
	constructor(page) {
		this.page = page;
		FutureDash.styles();
		this.f_period = page.add_field({
			fieldname: "period", label: __("Period"), fieldtype: "Select", default: "month",
			options: [
				{ value: "month", label: __("This month") }, { value: "last_month", label: __("Last month") },
				{ value: "30", label: __("Last 30 days") }, { value: "year", label: __("This year") }, { value: "custom", label: __("Custom range") },
			],
			change: () => { this.f_range.$wrapper.toggle(this.f_period.get_value() === "custom"); if (this.f_period.get_value() !== "custom") this.refresh(); },
		});
		this.f_range = page.add_field({ fieldname: "range", label: __("Date range"), fieldtype: "DateRange", change: () => this.refresh() });
		this.f_range.$wrapper.hide();
		page.set_primary_action(__("New Payment"), () => frappe.new_doc("Payment Approval Log"), "add");
		this.$root = $(`<div class="fd-root"></div>`).appendTo(page.main);
		$(window).on("resize.payments_dashboard", frappe.utils.debounce(() => this.draw_chart(), 150));
		this.refresh();
	}

	period() {
		const today = frappe.datetime.get_today();
		switch (this.f_period.get_value()) {
			case "last_month": {
				const start = frappe.datetime.add_months(frappe.datetime.month_start(), -1);
				return [start, frappe.datetime.add_days(frappe.datetime.month_start(), -1)];
			}
			case "30": return [frappe.datetime.add_days(today, -29), today];
			case "year": return [frappe.datetime.year_start(), today];
			case "custom": { const r = this.f_range.get_value(); return r && r[0] ? r : [frappe.datetime.month_start(), today]; }
			default: return [frappe.datetime.month_start(), today];
		}
	}

	refresh() {
		const [from_date, to_date] = this.period();
		this.$root.addClass("fd-loading");
		frappe
			.xcall("future.dashboards.payments_dashboard", { filters: { from_date, to_date } })
			.then((d) => { this.data = d; this.render(d); })
			.finally(() => this.$root.removeClass("fd-loading"));
	}

	open_list(doctype, filters) {
		frappe.route_options = Object.assign({}, filters);
		frappe.set_route("List", doctype);
	}

	render(d) {
		const D = FutureDash, k = d.kpis;
		const strip = D.strip([
			D.fig(__("Received"), D.money(k.total), __("{0} approved payments", [D.int(k.count)]), "lead", 'data-go="received"'),
			D.fig(__("Course fees"), D.money(k.course), ""),
			D.fig(__("Hostel"), D.money(k.hostel), ""),
			D.fig(__("Transport"), D.money(k.transport), ""),
			D.fig(__("Course fees owed"), D.money(k.outstanding), k.overdue ? __("{0} of it overdue", [D.money(k.overdue)]) : __("{0} students", [D.int(k.students_owing)]), k.overdue ? "neg" : ""),
		], "1.3fr 1fr 1fr 1fr 1.2fr");

		const queue = `<ul class="fd-queue">${d.queue
			.map((q, i) => `<li class="${q.n ? "" : "zero"}" data-q="${i}"><span>${D.esc(q.label)}</span><b>${q.n || "0"}</b></li>`)
			.join("")}</ul>`;

		const overdue = d.overdue.length
			? `<table class="fd-table"><thead><tr><th>${__("Student")}</th><th>${__("Overdue since")}</th><th class="num">${__("Amount")}</th></tr></thead><tbody>
				${d.overdue.map((r) => `<tr class="fd-click" data-enrollment="${D.esc(r.enrollment)}"><td>${D.esc(r.student_name)}<div class="fd-sub">${D.esc(r.program)}</div></td>
				<td>${D.date(r.since)}</td><td class="num">${D.money(r.amount)}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("No fee is overdue."));

		const recent = d.recent.length
			? `<table class="fd-table"><thead><tr><th>${__("Student")}</th><th class="num">${__("Amount")}</th></tr></thead><tbody>
				${d.recent.map((r) => `<tr class="fd-click" data-pal="${D.esc(r.name)}"><td class="fd-wrap">${D.esc(r.student_name)}
				<div class="fd-sub">${D.date(r.d)}${r.mode_of_payment ? " · " + D.esc(r.mode_of_payment) : ""}</div></td>
				<td class="num">${D.money(r.amount)}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("No approved payments yet."));

		this.$root.html(`
			${strip}
			<div class="fd-grid" style="grid-template-columns: minmax(0,1.7fr) minmax(0,1fr)">
				<div class="fd-grid">
					${D.card(__("Collections per day"), `<div class="fd-chart"></div>`, `<span class="fd-sub">${D.date(d.period.from_date)} – ${D.date(d.period.to_date)}</span>`)}
					${D.card(__("Overdue fees to chase"), overdue, `<span class="fd-sub">${__("course and hostel")}</span>`)}
				</div>
				<div class="fd-grid">
					${D.card(__("Waiting on you"), queue)}
					${D.card(__("By payment mode"), D.bars(d.modes, D.money))}
					${D.card(__("Latest payments"), recent, `<a class="fd-link" data-go="all">${__("All")} →</a>`)}
				</div>
			</div>`);
		this.draw_chart();

		this.$root.find("[data-q]").on("click", (e) => { const q = d.queue[+$(e.currentTarget).attr("data-q")]; this.open_list(q.doctype, q.filters); });
		this.$root.find("[data-enrollment]").on("click", (e) => frappe.set_route("Form", "Program Enrollment", $(e.currentTarget).attr("data-enrollment")));
		this.$root.find("[data-pal]").on("click", (e) => frappe.set_route("Form", "Payment Approval Log", $(e.currentTarget).attr("data-pal")));
		this.$root.find('[data-go="received"], [data-go="all"]').on("click", () => this.open_list("Payment Approval Log", { docstatus: 1 }));
	}

	draw_chart() {
		if (!this.data) return;
		const $box = this.$root.find(".fd-chart");
		if (!$box.length) return;
		const total = this.data.trend.reduce((a, p) => a + p.amount, 0);
		if (!total) {
			$box.html(FutureDash.empty(__("No payments received in this period.")));
			return;
		}
		FutureDash.line($box, this.data.trend, { label: __("Received") });
	}
}
