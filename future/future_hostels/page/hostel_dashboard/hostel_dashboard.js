// Hostel Dashboard: is there room, and is the hostel money coming in?
frappe.pages["hostel-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Hostel Dashboard"), single_column: true });
	frappe.require("/assets/future/js/future_dash.js", () => {
		wrapper.hostel_dashboard = new HostelDashboard(page);
	});
};

frappe.pages["hostel-dashboard"].on_page_show = function (wrapper) {
	wrapper.hostel_dashboard && wrapper.hostel_dashboard.refresh();
};

class HostelDashboard {
	constructor(page) {
		this.page = page;
		FutureDash.styles();
		this.f_month = page.add_field({ fieldname: "month", label: __("Month"), fieldtype: "Date", default: frappe.datetime.month_start(), change: () => this.refresh() });
		this.f_location = page.add_field({ fieldname: "location", label: __("Location"), fieldtype: "Link", options: "Location", change: () => this.refresh() });
		page.add_inner_button(__("Fee Collection"), () => frappe.set_route("query-report", "Hostel Fee Collection"));
		page.add_inner_button(__("Hostellers"), () => this.hostellers());
		this.$root = $(`<div class="fd-root"></div>`).appendTo(page.main);
		this.refresh();
	}

	hostellers(extra = {}) {
		frappe.route_options = { docstatus: 1, custom_hosteller: "Hosteller", custom_hostel_status: "Allotted", ...extra };
		frappe.set_route("List", "Program Enrollment");
	}

	refresh() {
		this.$root.addClass("fd-loading");
		frappe
			.xcall("future.dashboards.hostel_dashboard", {
				filters: { month: this.f_month.get_value(), location: this.f_location.get_value() },
			})
			.then((d) => this.render(d))
			.finally(() => this.$root.removeClass("fd-loading"));
	}

	render(d) {
		const D = FutureDash, k = d.kpis;
		const month = frappe.datetime.str_to_obj(d.month).toLocaleDateString(undefined, { month: "long", year: "numeric" });
		const collected = k.month_due ? Math.round((k.month_paid * 100) / k.month_due) : 0;

		const strip = D.strip([
			D.fig(__("Occupancy"), `${k.pct}%`, __("{0} of {1} beds taken", [D.int(k.used), D.int(k.capacity)]), "lead"),
			D.fig(__("Free beds"), D.int(k.free), __("across active hostels")),
			D.fig(__("Due in {0}", [month]), D.money(k.month_due), k.month_due ? __("{0} collected ({1}%)", [D.money(k.month_paid), collected]) : __("nothing scheduled")),
			D.fig(__("Hostel balance"), D.money(k.balance), k.overdue ? __("{0} overdue", [D.money(k.overdue)]) : __("nothing overdue"), k.overdue ? "neg" : "", 'data-go="dues"'),
		], "1.2fr 1fr 1fr 1fr");

		const hostels = d.hostels.length
			? `<table class="fd-table"><thead><tr><th>${__("Hostel")}</th><th>${__("Location")}</th><th class="num">${__("AC")}</th><th class="num">${__("Non AC")}</th>
				<th class="num">${__("Free")}</th><th>${__("Occupancy")}</th><th class="num">${__("Balance")}</th></tr></thead><tbody>
				${d.hostels.map((h) => `<tr class="fd-click ${h.capacity ? "" : "fd-dim"}" data-hostel="${D.esc(h.hostel)}">
					<td>${D.esc(h.name)}</td><td>${D.esc(h.location || "")}</td>
					<td class="num">${h.ac[1] ? `${h.ac[0]} / ${h.ac[1]}` : "—"}</td><td class="num">${h.non_ac[1] ? `${h.non_ac[0]} / ${h.non_ac[1]}` : "—"}</td>
					<td class="num">${h.capacity ? h.free : "—"}</td><td>${h.capacity ? D.meter(h.pct, h.pct >= 100) : '<span class="fd-sub">beds not set</span>'}</td>
					<td class="num">${h.balance ? D.money(h.balance) : "—"}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("No active hostels here"));

		const chase = d.to_chase.length
			? `<table class="fd-table"><thead><tr><th>${__("Student")}</th><th>${__("Overdue since")}</th><th class="num">${__("Amount")}</th></tr></thead><tbody>
				${d.to_chase.map((r) => `<tr class="fd-click" data-enrollment="${D.esc(r.enrollment)}"><td>${D.esc(r.student_name)}<div class="fd-sub">${D.esc(r.hostel_name || "")}</div></td>
				<td>${D.date(r.since)}</td><td class="num">${D.money(r.overdue)}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("No hostel fee is overdue."));

		const tone = { Allotted: "pos", Transferred: "", Vacated: "warn" };
		const moves = d.moves.length
			? `<table class="fd-table"><tbody>${d.moves.map((m) => `<tr class="fd-click" data-enrollment="${D.esc(m.enrollment)}">
				<td>${D.esc(m.student_name)}<div class="fd-sub">${D.esc([m.hostel_name, m.room_type].filter(Boolean).join(" · "))}</div></td>
				<td>${D.pill(__(m.log_type), tone[m.log_type])}</td><td class="num">${D.date(m.log_date)}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("No allotments yet."));

		this.$root.html(`
			${strip}
			<div class="fd-grid" style="grid-template-columns: minmax(0,1.7fr) minmax(0,1fr)">
				${D.card(__("Hostels"), hostels, `<span class="fd-sub">${__("Click a hostel to see its students")}</span>`)}
				<div class="fd-grid">
					${D.card(__("Hostel fees to chase"), chase, `<a class="fd-link" data-go="report">${__("Fee collection")} →</a>`)}
					${D.card(__("Recent movements"), moves)}
				</div>
			</div>`);

		this.$root.find("[data-hostel]").on("click", (e) => this.hostellers({ custom_hostel: $(e.currentTarget).attr("data-hostel") }));
		this.$root.find("[data-enrollment]").on("click", (e) => frappe.set_route("Form", "Program Enrollment", $(e.currentTarget).attr("data-enrollment")));
		this.$root.find('[data-go="dues"]').on("click", () => this.hostellers({ custom_hostel_balance: [">", 0] }));
		this.$root.find('[data-go="report"]').on("click", () => frappe.set_route("query-report", "Hostel Fee Collection"));
	}
}
