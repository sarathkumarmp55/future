// Lead Dashboard — /desk/lead-dashboard
// All numbers come from future.future.page.lead_dashboard.lead_dashboard.get_data,
// which is scoped by the user's lead visibility (own / team / all).

const LD_METHOD = "future.future.page.lead_dashboard.lead_dashboard.get_data";

frappe.pages["lead-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Lead Dashboard"),
		single_column: true,
	});
	wrapper.lead_dashboard = new LeadDashboard(page, wrapper);
};

frappe.pages["lead-dashboard"].on_page_show = function (wrapper) {
	wrapper.lead_dashboard && wrapper.lead_dashboard.refresh();
};

class LeadDashboard {
	constructor(page, wrapper) {
		this.page = page;
		this.wrapper = wrapper;
		this.data = null;
		inject_styles();
		this.make_filters();
		this.$root = $(`<div class="ld-root"></div>`).appendTo(page.main);
		this.$tip = $(`<div class="ld-tip" role="tooltip"></div>`).appendTo(document.body);
		this.page.set_primary_action(__("New Lead"), () => frappe.new_doc("Lead"), "add");
		this.page.add_inner_button(__("Lead List"), () => frappe.set_route("List", "Lead"));
		this.page.add_inner_button(__("Refresh"), () => this.refresh());
		$(window).on("resize.lead_dashboard", frappe.utils.debounce(() => this.draw_trend(), 150));
		this.refresh();
	}

	make_filters() {
		const me = this;
		this.f_period = this.page.add_field({
			fieldname: "period",
			label: __("Period"),
			fieldtype: "Select",
			options: [
				{ value: "today", label: __("Today") },
				{ value: "7", label: __("Last 7 days") },
				{ value: "30", label: __("Last 30 days") },
				{ value: "month", label: __("This month") },
				{ value: "90", label: __("Last 90 days") },
				{ value: "custom", label: __("Custom range") },
			],
			default: "30",
			change() {
				me.f_range.$wrapper.toggle(this.get_value() === "custom");
				if (this.get_value() !== "custom") me.refresh();
			},
		});
		this.f_range = this.page.add_field({
			fieldname: "range",
			label: __("Date range"),
			fieldtype: "DateRange",
			change: () => this.refresh(),
		});
		this.f_range.$wrapper.hide();
		this.f_source = this.page.add_field({
			fieldname: "source",
			label: __("Source"),
			fieldtype: "Link",
			options: "UTM Source",
			change: () => this.refresh(),
		});
		this.f_course = this.page.add_field({
			fieldname: "course_category",
			label: __("Course"),
			fieldtype: "Select",
			options: [
				"",
				"School Tuition",
				"Higher Secondary",
				"NEET & JEE Programs",
				"Integrated School Program",
			],
			change: () => this.refresh(),
		});
		this.f_location = this.page.add_field({
			fieldname: "location",
			label: __("Location"),
			fieldtype: "Link",
			options: "Location",
			change: () => this.refresh(),
		});
		this.f_member = this.page.add_field({
			fieldname: "member",
			label: __("Team member"),
			fieldtype: "Select",
			options: [""],
			change: () => this.refresh(),
		});
		this.f_member.$wrapper.hide();
	}

	get_filters() {
		const today = frappe.datetime.get_today();
		const period = this.f_period.get_value() || "30";
		let from_date = today;
		let to_date = today;
		if (period === "custom") {
			const r = this.f_range.get_value();
			if (r && r[0] && r[1]) [from_date, to_date] = r;
		} else if (period === "month") {
			from_date = frappe.datetime.month_start();
		} else if (period !== "today") {
			from_date = frappe.datetime.add_days(today, -(parseInt(period, 10) - 1));
		}
		return {
			from_date,
			to_date,
			source: this.f_source.get_value() || "",
			course_category: this.f_course.get_value() || "",
			location: this.f_location.get_value() || "",
			member: this.f_member.get_value() || "",
		};
	}

	refresh() {
		if (this._loading) return;
		this._loading = true;
		this.$root.addClass("ld-loading");
		frappe
			.xcall(LD_METHOD, { filters: this.get_filters() })
			.then((data) => {
				this.data = data;
				this.render();
			})
			.finally(() => {
				this._loading = false;
				this.$root.removeClass("ld-loading");
			});
	}

	update_member_filter(d) {
		const show = d.role !== "lead_user" && d.members.length;
		this.f_member.$wrapper.toggle(!!show);
		if (!show) return;
		const current = this.f_member.get_value();
		const opts = [{ value: "", label: __("Everyone") }].concat(d.members);
		const key = JSON.stringify(opts);
		if (this._member_key !== key) {
			this._member_key = key;
			this.f_member.df.options = opts;
			this.f_member.refresh();
			this.f_member.set_value(current || "");
		}
	}

	render() {
		const d = this.data;
		this.update_member_filter(d);
		const scope = {
			lead_user: __("My leads"),
			team_lead: __("My team"),
			lead_manager: __("My teams"),
			manager: __("All teams"),
		}[d.role];

		this.$root.html(`
			<div class="ld-head">
				<div>
					<div class="ld-scope">${frappe.utils.icon("lock", "xs")} ${scope}</div>
					<div class="ld-period">${frappe.datetime.str_to_user(d.period.from_date)} – ${frappe.datetime.str_to_user(d.period.to_date)}</div>
				</div>
			</div>
			<div class="ld-kpis">${this.kpis_html(d)}</div>
			<div class="ld-grid ld-grid-2">
				<section class="ld-card"><header><h4>${__("Pipeline")}</h4><span class="ld-sub">${__("Leads that reached each stage")}</span></header>${this.funnel_html(d)}</section>
				<section class="ld-card"><header><h4>${__("New leads per day")}</h4><span class="ld-sub">${__("Hover for the day's numbers")}</span></header><div class="ld-trend"></div></section>
			</div>
			<div class="ld-grid ld-grid-3">
				<section class="ld-card">${this.followups_html(d.followups)}</section>
				<section class="ld-card"><header><h4>${__("By source")}</h4></header>${this.bars_html(d.sources)}</section>
				<section class="ld-card"><header><h4>${__("By course")}</h4></header>${this.bars_html(d.courses)}</section>
			</div>
			<div class="ld-grid ${d.handovers ? "ld-grid-2" : ""}">
				<section class="ld-card">${this.opps_html(d.opportunities)}</section>
				${d.handovers ? `<section class="ld-card">${this.handovers_html(d.handovers, d.pending_requests)}</section>` : ""}
			</div>
			${d.team ? this.team_html(d.team) : ""}
			<section class="ld-card">
				<header><h4>${__("Latest leads")}</h4><a class="ld-link" href="/desk/lead">${__("View all")} →</a></header>
				${this.recent_html(d.recent)}
			</section>
		`);
		this.draw_trend();
		this.bind_tips();
	}

	kpis_html(d) {
		const k = d.kpis;
		const pct = (n) => (k.total ? Math.round((n * 100) / k.total) : 0);
		let delta = "";
		if (k.previous_total || k.total) {
			const diff = k.total - k.previous_total;
			const cls = diff > 0 ? "up" : diff < 0 ? "down" : "flat";
			const sign = diff > 0 ? "+" : "";
			delta = `<span class="ld-delta ${cls}">${sign}${diff} ${__("vs previous period")}</span>`;
		}
		const tile = (label, value, foot, accent = "") => `
			<div class="ld-kpi ${accent}">
				<div class="ld-kpi-label">${label}</div>
				<div class="ld-kpi-value">${value}</div>
				<div class="ld-kpi-foot">${foot}</div>
			</div>`;
		return [
			tile(__("Leads"), fmt_int(k.total), delta || "&nbsp;", "ld-kpi-hero"),
			tile(__("Contacted"), fmt_int(k.contacted), __("{0}% of leads", [pct(k.contacted)])),
			tile(__("Interested"), fmt_int(k.interested), __("{0}% of leads", [pct(k.interested)])),
			tile(__("Admissions"), fmt_int(k.won), __("{0}% conversion", [k.conversion])),
			tile(
				__("Not yet called"),
				fmt_int(k.untouched),
				k.late
					? `<span class="ld-late">${frappe.utils.icon("alert-triangle", "xs")} ${__("{0} past the {1}h first-call limit", [fmt_int(k.late), k.sla_hours])}</span>`
					: __("All within the {0}h first-call limit", [k.sla_hours]),
				k.late ? "ld-kpi-alert" : ""
			),
			tile(__("Lost"), fmt_int(k.lost), __("Disqualified, invalid or lost")),
		].join("");
	}

	funnel_html(d) {
		const k = d.kpis;
		const steps = [
			[__("All leads"), k.total],
			[__("Contacted"), k.contacted],
			[__("Interested"), k.interested],
			[__("Admission"), k.won],
		];
		if (!k.total) return empty_html(__("No leads in this period"));
		return `<div class="ld-funnel">${steps
			.map(([label, n], i) => {
				const w = Math.max((n / k.total) * 100, n ? 2 : 0);
				const prev = i ? steps[i - 1][1] : null;
				const drop = prev ? Math.round((n * 100) / prev) : null;
				return `<div class="ld-fstep" data-tip="${frappe.utils.escape_html(
					`${label}: ${n}` + (drop !== null ? ` · ${drop}% of previous stage` : "")
				)}">
					<div class="ld-flabel">${label}</div>
					<div class="ld-ftrack"><div class="ld-fbar ld-f${i}" style="width:${w}%"></div></div>
					<div class="ld-fval">${fmt_int(n)}${
						drop !== null ? `<span class="ld-muted"> · ${drop}%</span>` : ""
					}</div>
				</div>`;
			})
			.join("")}</div>`;
	}

	bars_html(rows) {
		if (!rows || !rows.length) return empty_html(__("No data"));
		const max = Math.max(...rows.map((r) => r.n));
		return `<div class="ld-bars">${rows
			.map(
				(r) => `<div class="ld-bar-row" data-tip="${frappe.utils.escape_html(
					`${r.label}: ${r.n} leads · ${r.won} admissions`
				)}">
					<div class="ld-bar-label" title="${frappe.utils.escape_html(r.label)}">${frappe.utils.escape_html(__(r.label))}</div>
					<div class="ld-bar-track"><div class="ld-bar" style="width:${Math.max((r.n / max) * 100, 2)}%"></div></div>
					<div class="ld-bar-val">${fmt_int(r.n)}</div>
				</div>`
			)
			.join("")}</div>`;
	}

	followups_html(f) {
		const c = f.counts;
		const list = f.items.length
			? f.items
					.map(
						(t) => `<a class="ld-task" href="/desk/lead/${encodeURIComponent(t.lead)}">
					<span class="ld-pill ${t.when}">${
						t.when === "overdue"
							? `${frappe.utils.icon("alert-triangle", "xs")} ${__("Overdue")}`
							: __("Today")
					}</span>
					<span class="ld-task-main">
						<b>${frappe.utils.escape_html(t.lead_name || t.lead)}</b>
						<span class="ld-muted">${frappe.utils.escape_html(t.description || t.status || "")}</span>
					</span>
					<span class="ld-muted ld-nowrap">${t.date ? frappe.datetime.str_to_user(t.date) : ""}</span>
				</a>`
					)
					.join("")
			: empty_html(__("Nothing due. Nice work."));
		return `<header><h4>${__("My follow-ups")}</h4><a class="ld-link" href="/desk/todo?status=Open&reference_type=Lead">${__("All")} →</a></header>
			<div class="ld-fu-counts">
				<div class="ld-fu ${c.overdue ? "overdue" : ""}"><b>${c.overdue}</b><span>${__("Overdue")}</span></div>
				<div class="ld-fu"><b>${c.today}</b><span>${__("Due today")}</span></div>
				<div class="ld-fu"><b>${c.upcoming}</b><span>${__("Upcoming")}</span></div>
			</div>
			<div class="ld-tasks">${list}</div>`;
	}

	opps_html(o) {
		const stat = (label, value) =>
			`<div class="ld-fu"><b>${value}</b><span>${label}</span></div>`;
		return `<header><h4>${__("Opportunities")}</h4><a class="ld-link" href="/desk/opportunity">${__("View all")} →</a></header>
			<div class="ld-fu-counts">
				${stat(__("Open"), fmt_int(o.open))}
				${stat(__("Open value"), format_currency(o.open_amount, null, 0))}
				${stat(__("Converted"), fmt_int(o.won))}
			</div>
			${o.total ? this.bars_html(o.by_status) : empty_html(__("No opportunities in this period"))}`;
	}

	handovers_html(rows, pending) {
		const list = rows.length
			? rows
					.map(
						(r) => `<a class="ld-task" href="/desk/lead-handover/${encodeURIComponent(r.name)}">
				<span class="ld-pill today">${frappe.utils.icon("arrow-right-left", "xs")} ${r.total_leads}</span>
				<span class="ld-task-main">
					<b>${frappe.utils.escape_html(r.to_name)}</b>
					<span class="ld-muted">${frappe.utils.escape_html(__("by {0}", [r.by_name]))} · ${frappe.utils.escape_html(r.reason || "")}</span>
				</span>
				<span class="ld-muted ld-nowrap">${r.handover_on ? frappe.datetime.comment_when(r.handover_on) : ""}</span>
			</a>`
					)
					.join("")
			: empty_html(__("No hand-overs yet"));
		const req = pending
			? `<a class="ld-request" href="/desk/lead-handover?docstatus=0&request_status=Requested">${frappe.utils.icon("bell", "xs")} ${__(
					"{0} hand-over request(s) waiting for approval",
					[pending]
			  )} →</a>`
			: "";
		return `<header><h4>${__("Recent hand-overs")}</h4><a class="ld-link" href="/desk/lead-handover/new">${__("New hand-over")} →</a></header>
			${req}<div class="ld-tasks">${list}</div>`;
	}

	team_html(rows) {
		if (!rows.length)
			return `<section class="ld-card"><header><h4>${__("Team performance")}</h4></header>${empty_html(
				__("No assigned leads in this period")
			)}</section>`;
		const max_conv = Math.max(...rows.map((r) => r.conversion), 1);
		return `<section class="ld-card">
			<header><h4>${__("Team performance")}</h4><span class="ld-sub">${frappe.utils.icon("lock", "xs")} ${__(
			"Only visible to team leads and managers"
		)}</span></header>
			<div class="ld-table-wrap"><table class="ld-table">
				<thead><tr>
					<th>${__("Salesperson")}</th><th class="num">${__("Assigned")}</th><th class="num">${__("Contacted")}</th>
					<th class="num">${__("Interested")}</th><th class="num">${__("Admissions")}</th>
					<th>${__("Conversion")}</th><th class="num">${__("Overdue tasks")}</th>
				</tr></thead>
				<tbody>${rows
					.map(
						(r) => `<tr>
					<td><span class="ld-avatar">${frappe.avatar(r.user, "avatar-small")}</span>${frappe.utils.escape_html(r.full_name)}</td>
					<td class="num">${r.assigned}</td><td class="num">${r.contacted}</td>
					<td class="num">${r.interested}</td><td class="num"><b>${r.won}</b></td>
					<td><div class="ld-conv"><div class="ld-conv-track"><div class="ld-conv-bar" style="width:${
						(r.conversion / max_conv) * 100
					}%"></div></div><span>${r.conversion}%</span></div></td>
					<td class="num">${
						r.overdue
							? `<span class="ld-pill overdue">${frappe.utils.icon("alert-triangle", "xs")} ${r.overdue}</span>`
							: `<span class="ld-muted">0</span>`
					}</td>
				</tr>`
					)
					.join("")}</tbody>
			</table></div>
		</section>`;
	}

	recent_html(rows) {
		if (!rows.length) return empty_html(__("No leads in this period"));
		return `<div class="ld-table-wrap"><table class="ld-table">
			<thead><tr><th>${__("Lead")}</th><th>${__("Mobile")}</th><th>${__("Course")}</th><th>${__(
			"Source"
		)}</th><th>${__("Status")}</th><th>${__("Created")}</th></tr></thead>
			<tbody>${rows
				.map(
					(r) => `<tr class="ld-click" data-name="${frappe.utils.escape_html(r.name)}">
				<td><b>${frappe.utils.escape_html(r.lead_name || r.name)}</b></td>
				<td>${frappe.utils.escape_html(r.mobile_no || "")}</td>
				<td>${frappe.utils.escape_html(r.course || "")}</td>
				<td>${frappe.utils.escape_html(r.source || "")}</td>
				<td><span class="ld-status">${frappe.utils.escape_html(__(r.status || ""))}</span></td>
				<td class="ld-muted ld-nowrap">${frappe.datetime.comment_when(r.creation)}</td>
			</tr>`
				)
				.join("")}</tbody></table></div>`;
	}

	draw_trend() {
		if (!this.data) return;
		const $box = this.$root.find(".ld-trend");
		if (!$box.length) return;
		const pts = this.data.trend;
		const W = Math.max($box.width(), 280);
		const H = 220;
		const m = { t: 12, r: 12, b: 26, l: 34 };
		const iw = W - m.l - m.r;
		const ih = H - m.t - m.b;
		const max = Math.max(...pts.map((p) => p.leads), 1);
		const nice = nice_max(max);
		const x = (i) => m.l + (pts.length === 1 ? iw / 2 : (i * iw) / (pts.length - 1));
		const y = (v) => m.t + ih - (v / nice) * ih;

		const ticks = [0, nice / 2, nice].map((v) => Math.round(v));
		const grid = ticks
			.map(
				(t) => `<line x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}" class="ld-grid-line"/>
				<text x="${m.l - 6}" y="${y(t) + 4}" text-anchor="end" class="ld-axis">${t}</text>`
			)
			.join("");
		const step = Math.ceil(pts.length / Math.max(Math.floor(iw / 70), 1));
		const xlabels = pts
			.map((p, i) =>
				(i % step === 0 && pts.length - 1 - i >= step * 0.6) || i === pts.length - 1
					? `<text x="${x(i)}" y="${H - 6}" text-anchor="middle" class="ld-axis">${frappe.datetime
							.str_to_obj(p.date)
							.toLocaleDateString(undefined, { day: "numeric", month: "short" })}</text>`
					: ""
			)
			.join("");
		const line = pts.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.leads)}`).join(" ");
		const area = `${line} L${x(pts.length - 1)},${y(0)} L${x(0)},${y(0)} Z`;

		$box.html(`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${__(
			"New leads per day"
		)}">
			${grid}${xlabels}
			<path d="${area}" class="ld-area"/>
			<path d="${line}" class="ld-line"/>
			<line class="ld-cross" y1="${m.t}" y2="${m.t + ih}" style="display:none"/>
			<circle class="ld-dot" r="4.5" style="display:none"/>
			<rect class="ld-hit" x="${m.l}" y="${m.t}" width="${iw}" height="${ih}" fill="transparent"/>
		</svg>`);

		const $svg = $box.find("svg");
		const cross = $svg.find(".ld-cross")[0];
		const dot = $svg.find(".ld-dot")[0];
		$svg.find(".ld-hit")
			.on("mousemove", (e) => {
				const rect = $svg[0].getBoundingClientRect();
				const px = e.clientX - rect.left;
				const i = Math.min(
					pts.length - 1,
					Math.max(0, Math.round(((px - m.l) / iw) * (pts.length - 1)))
				);
				const p = pts[i];
				cross.setAttribute("x1", x(i));
				cross.setAttribute("x2", x(i));
				cross.style.display = "";
				dot.setAttribute("cx", x(i));
				dot.setAttribute("cy", y(p.leads));
				dot.style.display = "";
				this.show_tip(
					`<b>${frappe.datetime.str_to_user(p.date)}</b><br>${__("Leads")}: ${p.leads}<br>${__(
						"Admissions"
					)}: ${p.won}`,
					rect.left + x(i),
					rect.top + y(p.leads)
				);
			})
			.on("mouseleave", () => {
				cross.style.display = "none";
				dot.style.display = "none";
				this.hide_tip();
			});
	}

	bind_tips() {
		const me = this;
		this.$root
			.find("[data-tip]")
			.on("mousemove", function (e) {
				me.show_tip(frappe.utils.escape_html($(this).attr("data-tip")), e.clientX, e.clientY - 6);
			})
			.on("mouseleave", () => this.hide_tip());
		this.$root.find(".ld-click").on("click", function () {
			frappe.set_route("Form", "Lead", $(this).attr("data-name"));
		});
	}

	show_tip(html, x, y) {
		this.$tip.html(html).css({ left: x, top: y }).addClass("show");
	}

	hide_tip() {
		this.$tip.removeClass("show");
	}
}

function fmt_int(n) {
	return format_number(n || 0, null, 0);
}

function nice_max(v) {
	if (v <= 5) return 5;
	const p = Math.pow(10, Math.floor(Math.log10(v)));
	for (const s of [1, 2, 2.5, 5, 10]) if (s * p >= v) return s * p;
	return 10 * p;
}

function empty_html(msg) {
	return `<div class="ld-empty">${msg}</div>`;
}

function inject_styles() {
	if (document.getElementById("ld-styles")) return;
	const css = `
.ld-root {
	--ld-blue-1: #86b6ef; --ld-blue-2: #5598e7; --ld-blue-3: #2a78d6; --ld-blue-4: #1c5cab;
	--ld-series: #2a78d6; --ld-series-soft: rgba(42,120,214,.12);
	--ld-critical: #c62a2f; --ld-critical-bg: rgba(227,73,72,.12);
	--ld-warn: #a35f00; --ld-warn-bg: rgba(237,161,0,.14);
	--ld-good: #0f7a48;
	padding: 4px 16px 40px; box-sizing: border-box; max-width: 100%; transition: opacity .15s;
}
[data-theme="dark"] .ld-root {
	--ld-blue-1: #184f95; --ld-blue-2: #256abf; --ld-blue-3: #3987e5; --ld-blue-4: #6da7ec;
	--ld-series: #3987e5; --ld-series-soft: rgba(57,135,229,.18);
	--ld-critical: #f08585; --ld-critical-bg: rgba(230,103,103,.16);
	--ld-warn: #f0b84a; --ld-warn-bg: rgba(201,133,0,.2);
	--ld-good: #4cc38a;
}
.ld-root.ld-loading { opacity: .55; pointer-events: none; }
.ld-head { display:flex; justify-content:space-between; align-items:flex-end; margin: 4px 0 14px; }
.ld-scope { display:inline-flex; gap:6px; align-items:center; font-size: var(--text-sm); font-weight:600;
	color: var(--text-color); background: var(--subtle-fg, var(--control-bg)); border:1px solid var(--border-color);
	padding: 3px 10px; border-radius: 999px; }
.ld-period { color: var(--text-muted); font-size: var(--text-sm); margin-top:6px; }
.ld-kpis { display:grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap:12px; margin-bottom:12px; }
.ld-kpi { background: var(--card-bg); border:1px solid var(--border-color); border-radius: 12px; padding: 14px 16px; }
.ld-kpi-hero { background: linear-gradient(135deg, var(--ld-series-soft), transparent 70%), var(--card-bg); }
.ld-kpi-label { color: var(--text-muted); font-size: var(--text-sm); }
.ld-kpi-value { font-size: 28px; font-weight: 650; letter-spacing: -.02em; color: var(--heading-color, var(--text-color)); margin: 4px 0 2px; font-variant-numeric: tabular-nums; }
.ld-kpi-foot { color: var(--text-muted); font-size: var(--text-xs); min-height: 16px; }
.ld-delta.up { color: var(--ld-good); } .ld-delta.down { color: var(--ld-critical); }
.ld-grid { display:grid; gap:12px; margin-bottom:12px; }
.ld-grid-2 { grid-template-columns: 5fr 7fr; }
.ld-grid-3 { grid-template-columns: repeat(3, minmax(0,1fr)); }
.ld-card { background: var(--card-bg); border:1px solid var(--border-color); border-radius: 12px; padding: 16px 18px; min-width:0; margin-bottom: 12px; }
.ld-grid > .ld-card { margin-bottom: 0; }
.ld-card header { display:flex; align-items:baseline; justify-content:space-between; gap:8px; margin-bottom: 14px; flex-wrap: wrap; }
.ld-card h4 { margin:0; font-size: var(--text-base); font-weight:600; color: var(--heading-color, var(--text-color)); }
.ld-sub, .ld-muted { color: var(--text-muted); font-size: var(--text-xs); }
.ld-link { font-size: var(--text-sm); color: var(--text-muted); } .ld-link:hover { color: var(--text-color); }
.ld-funnel { display:flex; flex-direction:column; gap:14px; padding-top:4px; }
.ld-fstep { display:grid; grid-template-columns: 92px 1fr 110px; align-items:center; gap:10px; }
.ld-flabel { font-size: var(--text-sm); color: var(--text-color); }
.ld-ftrack, .ld-bar-track, .ld-conv-track { background: var(--control-bg); border-radius: 4px; height: 22px; overflow:hidden; }
.ld-fbar { height:100%; border-radius: 4px; transition: width .4s ease; }
.ld-f0 { background: var(--ld-blue-1); } .ld-f1 { background: var(--ld-blue-2); }
.ld-f2 { background: var(--ld-blue-3); } .ld-f3 { background: var(--ld-blue-4); }
.ld-fval, .ld-bar-val { font-size: var(--text-sm); font-weight:600; text-align:right; font-variant-numeric: tabular-nums; color: var(--text-color); }
.ld-trend { min-height: 220px; }
.ld-trend svg { display:block; overflow: visible; }
.ld-grid-line { stroke: var(--border-color); stroke-width:1; }
.ld-axis { fill: var(--text-muted); font-size: 11px; }
.ld-line { fill:none; stroke: var(--ld-series); stroke-width:2; stroke-linejoin: round; stroke-linecap: round; }
.ld-area { fill: var(--ld-series-soft); }
.ld-cross { stroke: var(--text-muted); stroke-width:1; stroke-dasharray: 3 3; }
.ld-dot { fill: var(--ld-series); stroke: var(--card-bg); stroke-width:2; }
.ld-bars { display:flex; flex-direction:column; gap:9px; }
.ld-bar-row { display:grid; grid-template-columns: minmax(80px, 38%) 1fr 40px; gap:10px; align-items:center; }
.ld-bar-label { font-size: var(--text-sm); color: var(--text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ld-bar-track { height: 10px; } .ld-bar { height:100%; background: var(--ld-series); border-radius: 4px; }
.ld-fu-counts { display:grid; grid-template-columns: repeat(3,1fr); gap:8px; margin-bottom:12px; }
.ld-fu { background: var(--control-bg); border-radius: 8px; padding: 8px 10px; display:flex; flex-direction:column; }
.ld-fu b { font-size: 20px; font-variant-numeric: tabular-nums; color: var(--text-color); }
.ld-fu span { font-size: var(--text-xs); color: var(--text-muted); }
.ld-fu.overdue { background: var(--ld-critical-bg); } .ld-fu.overdue b { color: var(--ld-critical); }
.ld-tasks { display:flex; flex-direction:column; max-height: 230px; overflow:auto; }
.ld-task { display:grid; grid-template-columns: auto 1fr auto; gap:10px; align-items:center; padding: 8px 4px; border-top:1px solid var(--border-color); color: var(--text-color); text-decoration:none; }
.ld-task:hover { background: var(--control-bg); text-decoration:none; }
.ld-task-main { display:flex; flex-direction:column; min-width:0; }
.ld-task-main .ld-muted { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ld-pill { display:inline-flex; align-items:center; gap:4px; font-size: var(--text-xs); font-weight:600; padding: 2px 8px; border-radius: 999px; white-space:nowrap; }
.ld-pill.overdue { color: var(--ld-critical); background: var(--ld-critical-bg); }
.ld-pill.today { color: var(--ld-warn); background: var(--ld-warn-bg); }
.ld-pill .icon { stroke: currentColor; }
.ld-table-wrap { overflow-x:auto; }
.ld-table { width:100%; border-collapse: collapse; font-size: var(--text-sm); }
.ld-table th { color: var(--text-muted); font-weight:500; text-align:left; padding: 6px 10px; border-bottom:1px solid var(--border-color); white-space:nowrap; }
.ld-table td { padding: 9px 10px; border-bottom:1px solid var(--border-color); color: var(--text-color); white-space:nowrap; }
.ld-table tr:last-child td { border-bottom: 0; }
.ld-table .num { text-align:right; font-variant-numeric: tabular-nums; }
.ld-click { cursor:pointer; } .ld-click:hover td { background: var(--control-bg); }
.ld-avatar { margin-right: 8px; display:inline-block; vertical-align: middle; }
.ld-conv { display:flex; align-items:center; gap:8px; min-width: 140px; }
.ld-conv-track { flex:1; height: 8px; } .ld-conv-bar { height:100%; background: var(--ld-series); border-radius:4px; }
.ld-conv span { font-variant-numeric: tabular-nums; width: 44px; text-align:right; }
.ld-status { font-size: var(--text-xs); background: var(--control-bg); padding: 2px 8px; border-radius: 999px; }
.ld-late { color: var(--ld-critical); display:inline-flex; gap:4px; align-items:center; }
.ld-late .icon { stroke: currentColor; }
.ld-kpi-alert { border-color: var(--ld-critical-bg); box-shadow: inset 0 3px 0 var(--ld-critical); }
.ld-request { display:flex; align-items:center; gap:6px; margin-bottom:10px; padding: 8px 10px; border-radius: 8px;
	background: var(--ld-warn-bg); color: var(--ld-warn); font-size: var(--text-sm); font-weight:600; }
.ld-request:hover { text-decoration:none; color: var(--ld-warn); }
.ld-request .icon { stroke: currentColor; }
.ld-empty { color: var(--text-muted); font-size: var(--text-sm); padding: 24px 0; text-align:center; }
.ld-nowrap { white-space:nowrap; }
.ld-tip { position: fixed; z-index: 1100; pointer-events:none; opacity:0; transform: translate(-50%, calc(-100% - 10px));
	background: var(--card-bg); color: var(--text-color); border:1px solid var(--border-color); box-shadow: var(--shadow-md);
	border-radius: 8px; padding: 6px 10px; font-size: var(--text-xs); line-height:1.5; transition: opacity .1s; white-space:nowrap; }
.ld-tip.show { opacity:1; }
@media (max-width: 1200px) { .ld-kpis { grid-template-columns: repeat(3, minmax(0,1fr)); } .ld-grid-3 { grid-template-columns: 1fr 1fr; } }
@media (max-width: 900px) { .ld-grid-2, .ld-grid-3 { grid-template-columns: 1fr; } }
@media (max-width: 560px) { .ld-kpis { grid-template-columns: 1fr 1fr; } .ld-fstep { grid-template-columns: 80px 1fr 70px; } }
`;
	const el = document.createElement("style");
	el.id = "ld-styles";
	el.textContent = css;
	document.head.appendChild(el);
}
