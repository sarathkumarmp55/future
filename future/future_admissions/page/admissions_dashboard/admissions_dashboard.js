// Admissions Dashboard: how is admission going, and who needs attention?
frappe.pages["admissions-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Admissions Dashboard"), single_column: true });
	frappe.require("/assets/future/js/future_dash.js", () => {
		wrapper.admissions_dashboard = new AdmissionsDashboard(page);
	});
};

frappe.pages["admissions-dashboard"].on_page_show = function (wrapper) {
	wrapper.admissions_dashboard && wrapper.admissions_dashboard.refresh();
};

class AdmissionsDashboard {
	constructor(page) {
		this.page = page;
		FutureDash.styles();
		this.f_period = page.add_field({
			fieldname: "period", label: __("Period"), fieldtype: "Select", default: "year",
			options: [
				{ value: "month", label: __("This month") }, { value: "30", label: __("Last 30 days") },
				{ value: "90", label: __("Last 90 days") }, { value: "year", label: __("Admission year") }, { value: "custom", label: __("Custom range") },
			],
			change: () => { this.f_range.$wrapper.toggle(this.f_period.get_value() === "custom"); if (this.f_period.get_value() !== "custom") this.refresh(); },
		});
		this.f_range = page.add_field({ fieldname: "range", label: __("Date range"), fieldtype: "DateRange", change: () => this.refresh() });
		this.f_range.$wrapper.hide();
		this.f_center = page.add_field({ fieldname: "center", label: __("Centre"), fieldtype: "Link", options: "Center", change: () => this.refresh() });
		this.f_vertical = page.add_field({
			fieldname: "vertical", label: __("Vertical"), fieldtype: "Select",
			options: ["", "FSP", "Repeaters", "Re-Repeaters", "Board + Entrance", "Board Prepartaion", "Crash Program"],
			change: () => this.refresh(),
		});
		page.add_inner_button(__("Admissions"), () => this.list({}));
		this.$root = $(`<div class="fd-root"></div>`).appendTo(page.main);
		$(window).on("resize.admissions_dashboard", frappe.utils.debounce(() => this.draw_chart(), 150));
		this.refresh();
	}

	period() {
		const today = frappe.datetime.get_today();
		switch (this.f_period.get_value()) {
			case "month": return [frappe.datetime.month_start(), today];
			case "30": return [frappe.datetime.add_days(today, -29), today];
			case "90": return [frappe.datetime.add_days(today, -89), today];
			case "custom": { const r = this.f_range.get_value(); return r && r[0] ? r : [frappe.datetime.month_start(), today]; }
			default: {
				// admission year runs from 1 April (the programmes start Apr-Jun)
				const t = frappe.datetime.str_to_obj(today);
				const y = t.getMonth() >= 3 ? t.getFullYear() : t.getFullYear() - 1;
				return [`${y}-04-01`, today];
			}
		}
	}

	list(extra) {
		const [from_date, to_date] = this.period();
		const opts = { docstatus: 1, enrollment_date: ["between", [from_date, to_date]], ...extra };
		if (this.f_center.get_value()) opts.custom_center = this.f_center.get_value();
		if (this.f_vertical.get_value()) opts.custom_vertical = this.f_vertical.get_value();
		frappe.route_options = opts;
		frappe.set_route("List", "Program Enrollment");
	}

	refresh() {
		const [from_date, to_date] = this.period();
		this.$root.addClass("fd-loading");
		frappe
			.xcall("future.dashboards.admissions_dashboard", {
				filters: { from_date, to_date, center: this.f_center.get_value(), vertical: this.f_vertical.get_value() },
			})
			.then((d) => { this.data = d; this.render(d); })
			.finally(() => this.$root.removeClass("fd-loading"));
	}

	render(d) {
		const D = FutureDash, k = d.kpis;
		const strip = D.strip([
			D.fig(__("Admissions"), D.int(k.total), `${D.date(d.period.from_date)} – ${D.date(d.period.to_date)}`, "lead", 'data-go="all"'),
			D.fig(__("Joined"), D.int(k.joined), __("{0}% of admissions", [k.joined_pct]), "", 'data-go="joined"'),
			D.fig(__("Waiting to join"), D.int(k.pending), __("paid, not joined yet"), "", 'data-go="pending"'),
			D.fig(__("Dropped or cancelled"), D.int(k.dropped), __("left the programme"), "", 'data-go="dropped"'),
			D.fig(__("Course fee collected"), `${k.paid_pct}%`, __("{0} of {1}", [D.money(k.paid), D.money(k.fee)])),
		], "1.2fr 1fr 1fr 1fr 1.2fr");

		const waiting = d.waiting.length
			? `<table class="fd-table"><thead><tr><th>${__("Student")}</th><th>${__("Enrolled")}</th><th class="num">${__("Waiting")}</th></tr></thead><tbody>
				${d.waiting.map((r) => `<tr class="fd-click" data-enrollment="${D.esc(r.enrollment)}"><td class="fd-wrap">${D.esc(r.student_name)}
				<div class="fd-sub">${D.esc([r.program, r.center].filter(Boolean).join(" · "))}</div></td>
				<td>${D.date(r.enrollment_date)}</td><td class="num">${r.days > 14 ? D.pill(__("{0} days", [r.days]), "warn") : __("{0} days", [r.days])}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("Everyone admitted in this period has joined."));

		const overdue = d.overdue.length
			? `<table class="fd-table"><tbody>${d.overdue.map((r) => `<tr class="fd-click" data-enrollment="${D.esc(r.enrollment)}">
				<td class="fd-wrap">${D.esc(r.student_name)}<div class="fd-sub">${D.esc(r.program)}</div></td><td class="num">${D.money(r.amount)}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("No course fee is overdue."));

		this.$root.html(`
			${strip}
			<div class="fd-grid" style="grid-template-columns: minmax(0,1.7fr) minmax(0,1fr)">
				<div class="fd-grid">
					${D.card(d.bucket === "week" ? __("Admissions per week") : __("Admissions per day"), `<div class="fd-chart"></div>`)}
					<div class="fd-grid" style="grid-template-columns: 1fr 1fr">
						${D.card(__("By programme"), D.bars(d.programs))}
						${D.card(__("By centre"), D.bars(d.centers))}
					</div>
				</div>
				<div class="fd-grid">
					${D.card(__("Waiting to join"), waiting, `<a class="fd-link" data-go="pending">${__("All")} →</a>`)}
					${D.card(__("Course fees overdue"), overdue, `<a class="fd-link" data-go="payments">${__("Payments")} →</a>`)}
					${D.card(__("Where they stay"), D.bars(d.stay))}
				</div>
			</div>`);
		this.draw_chart();

		const go = {
			all: () => this.list({}),
			joined: () => this.list({ custom_admission_status: "Joined" }),
			pending: () => this.list({ custom_admission_status: "Pending" }),
			dropped: () => this.list({ custom_admission_status: ["in", ["Dropped", "Cancelled"]] }),
			payments: () => frappe.set_route("payments-dashboard"),
		};
		this.$root.find("[data-go]").on("click", (e) => go[$(e.currentTarget).attr("data-go")]());
		this.$root.find("[data-enrollment]").on("click", (e) => frappe.set_route("Form", "Program Enrollment", $(e.currentTarget).attr("data-enrollment")));
	}

	draw_chart() {
		if (!this.data) return;
		const $box = this.$root.find(".fd-chart");
		if (!$box.length) return;
		if (!this.data.kpis.total) {
			$box.html(FutureDash.empty(__("No admissions in this period.")));
			return;
		}
		FutureDash.line($box, this.data.trend, { value: "count", fmt: FutureDash.int, label: __("Admissions") });
	}
}
