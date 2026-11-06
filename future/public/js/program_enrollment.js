// Program Enrollment: the student 360 view (fee progress, hostel, journey,
// extras, payments) above the form, plus schedule helpers.
// Data: future.admissions.get_enrollment_dashboard.

frappe.ui.form.on("Program Enrollment", {
	refresh(frm) {
		fe360_styles();
		frm.$wrapper.find(".fe-360").remove();
		if (frm.is_new()) return;

		const $box = $(`<div class="fe-360"><div class="fe-loading">${__("Loading…")}</div></div>`);
		$(frm.layout.wrapper).prepend($box);
		frappe
			.xcall("future.admissions.get_enrollment_dashboard", { name: frm.doc.name })
			.then((d) => $box.html(render_360(d)));

		if (frm.doc.docstatus < 2 && frm.perm[0]?.write) {
			frm.add_custom_button(
				__("Build Default Schedules"),
				() =>
					frappe.confirm(
						__("Replace the course (and hostel) fee schedule with the default one for this program?"),
						() =>
							frappe
								.xcall("future.admissions.make_schedules", { name: frm.doc.name })
								.then(() => frm.reload_doc())
					),
				__("Fees")
			);
		}
		if (frm.doc.docstatus === 1 && frm.perm[0]?.write) add_hostel_buttons(frm);
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Request Refund"), () =>
				frappe.new_doc("Fee Refund Request", { enrollment: frm.doc.name })
			, __("Fees"));
			frm.add_custom_button(__("Transfer Fee"), () =>
				frappe.new_doc("Fee Transfer Request", { from_enrollment: frm.doc.name })
			, __("Fees"));
		}
		if (frm.doc.docstatus === 1 && frm.doc.custom_admission_status === "Pending") {
			frm.add_custom_button(__("Mark as Joined"), () => {
				frappe.prompt(
					{ fieldname: "date", fieldtype: "Date", label: __("Date of Joining"), default: frappe.datetime.get_today(), reqd: 1 },
					(v) => {
						frm.set_value({ custom_has_joined: 1, custom_date_of_joined: v.date, custom_admission_status: "Joined" });
						frm.save("Update");
					},
					__("Mark as Joined")
				);
			});
		}
	},
	custom_offered_amount: set_final,
	custom_discount_amount: set_final,
	custom_has_joined(frm) {
		if (frm.doc.custom_has_joined && !frm.doc.custom_date_of_joined)
			frm.set_value("custom_date_of_joined", frappe.datetime.get_today());
	},
});

function add_hostel_buttons(frm) {
	const allotted = frm.doc.custom_hostel_status === "Allotted" && frm.doc.custom_hostel;
	const run = (method, args, msg) =>
		frappe.xcall(`future.hostel_management.${method}`, { name: frm.doc.name, ...args }).then(() => {
			frappe.show_alert({ message: msg, indicator: "green" });
			frm.reload_doc();
		});
	const pick = (title, action_label, current, on_ok) => {
		const d = new frappe.ui.Dialog({
			title,
			fields: [
				{ fieldname: "room_type", fieldtype: "Select", label: __("Room Type"), options: ["Non AC", "AC"], default: frm.doc.custom_hostel_type || "Non AC", reqd: 1,
				  change: () => load(d.get_value("room_type")) },
				{ fieldname: "hostel", fieldtype: "Autocomplete", label: __("Hostel"), reqd: 1, options: [] },
				{ fieldname: "date", fieldtype: "Date", label: __("From"), default: frappe.datetime.get_today(), reqd: 1 },
				{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes") },
			],
			primary_action_label: action_label,
			primary_action(v) {
				d.hide();
				on_ok(v);
			},
		});
		const load = (room_type) =>
			frappe.xcall("future.hostel_management.get_hostel_options", { room_type }).then((opts) => {
				const field = d.fields_dict.hostel;
				field.set_data(opts.filter((o) => o.value !== current || room_type !== frm.doc.custom_hostel_type));
			});
		d.show();
		load(d.get_value("room_type"));
	};

	if (!allotted) {
		frm.add_custom_button(__("Allot Hostel"), () =>
			pick(__("Allot hostel"), __("Allot"), null, (v) => run("allot", v, __("Hostel allotted")))
		, __("Hostel"));
	} else {
		frm.add_custom_button(__("Transfer Hostel"), () =>
			pick(__("Move to another hostel or room type"), __("Transfer"), frm.doc.custom_hostel, (v) => run("transfer", v, __("Hostel transferred")))
		, __("Hostel"));
		frm.add_custom_button(__("Vacate Hostel"), () =>
			frappe.prompt(
				[
					{ fieldname: "date", fieldtype: "Date", label: __("Vacating On"), default: frappe.datetime.get_today(), reqd: 1 },
					{ fieldname: "notes", fieldtype: "Small Text", label: __("Reason") },
				],
				(v) => run("vacate", v, __("Hostel vacated. Unpaid hostel fees after that date were removed.")),
				__("Vacate hostel"),
				__("Vacate")
			)
		, __("Hostel"));
	}
}

function set_final(frm) {
	frm.set_value("custom_final_amount", flt(frm.doc.custom_offered_amount) - flt(frm.doc.custom_discount_amount));
}

function render_360(d) {
	const e = d.enrollment, s = d.student, c = d.course, h = d.hostel, x = d.extras;
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));
	const money = (v) => format_currency(v || 0, null, 0);
	const date = (v) => (v ? frappe.datetime.str_to_user(v) : "—");
	const initials = (s.student_name || "?")
		.split(/\s+/)
		.slice(0, 2)
		.map((w) => w[0])
		.join("")
		.toUpperCase();
	const status_cls = { Pending: "warn", Joined: "good", Completed: "info", Dropped: "bad", Cancelled: "bad" }[e.status] || "muted";

	const alert = d.overdue
		? `<div class="fe-alert bad">${frappe.utils.icon("triangle-alert", "sm")}<span><b>${__("Overdue")}</b> ${__("{0} past its due date", [money(d.overdue)])}</span></div>`
		: c.balance
		? `<div class="fe-alert warn">${frappe.utils.icon("info", "sm")}<span><b>${__("Outstanding balance")}</b> ${__("{0} pending on course fee", [money(c.balance)])}${
				c.next_due ? ` · ${__("next {0} on {1}", [money(c.next_due.amount), date(c.next_due.date)])}` : ""
		  }</span></div>`
		: "";

	const chips = [
		`<span class="fe-chip ${status_cls}">${esc(__(e.status || "Pending"))}</span>`,
		e.program && `<span class="fe-chip info">${esc(e.program)}</span>`,
		e.center && `<span class="fe-chip">${esc(e.center)}</span>`,
		e.program_type && `<span class="fe-chip">${esc(e.program_type)}${e.vertical ? " · " + esc(e.vertical) : ""}</span>`,
		e.academic_year && `<span class="fe-chip">${esc(e.academic_year)}</span>`,
		e.hosteller && `<span class="fe-chip">${esc(__(e.hosteller))}</span>`,
	]
		.filter(Boolean)
		.join("");

	const link = (route, name) => `<a href="/desk/${route}/${encodeURIComponent(name)}">${esc(name)}</a>`;
	const chip = (status) => {
		const tone = { Approved: "good", Paid: "good", Pending: "warn", Requested: "warn", Waiting: "warn", Rejected: "bad", Cancelled: "bad" }[status] || "";
		return `<span class="fe-chip ${tone}">${esc(__(status || ""))}</span>`;
	};
	const money_card = (title, icon, rows, headers, cells, empty) => `
		<section class="fe-card"><header><span class="fe-ico">${frappe.utils.icon(icon, "sm")}</span><div><h5>${title}</h5></div></header>
		${rows.length
			? `<div class="fe-table-wrap"><table class="fe-table"><thead><tr>${headers.map((h, i) => `<th class="${i === 2 ? "num" : ""}">${h}</th>`).join("")}</tr></thead>
				<tbody>${rows.map((r) => `<tr>${cells(r).map((c, i) => `<td class="${i === 2 ? "num" : ""}">${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
			: `<div class="fe-empty">${empty}</div>`}
		</section>`;
	const tile = (label, value, foot, cls = "") => `
		<div class="fe-tile ${cls}"><div class="fe-label">${label}</div><div class="fe-value">${value}</div><div class="fe-foot">${foot}</div></div>`;

	const ring = (pct) => {
		const r = 34, len = 2 * Math.PI * r, off = len * (1 - Math.min(pct, 100) / 100);
		return `<svg class="fe-ring" viewBox="0 0 84 84" role="img" aria-label="${pct}% paid">
			<circle cx="42" cy="42" r="${r}" class="fe-ring-track"/>
			<circle cx="42" cy="42" r="${r}" class="fe-ring-bar" stroke-dasharray="${len}" stroke-dashoffset="${off}" transform="rotate(-90 42 42)"/>
			<text x="42" y="40" text-anchor="middle" class="fe-ring-pct">${pct}%</text>
			<text x="42" y="55" text-anchor="middle" class="fe-ring-sub">${__("paid")}</text></svg>`;
	};

	const progress = (title, sub, total, paid, balance, pct, icon) => `
		<section class="fe-card">
			<header><span class="fe-ico">${frappe.utils.icon(icon, "sm")}</span><div><h5>${title}</h5><span class="fe-muted">${sub}</span></div>
				<span class="fe-chip ${pct >= 100 ? "good" : "info"}">${__("{0}% collected", [pct])}</span></header>
			<div class="fe-progress">
				${ring(pct)}
				<div class="fe-progress-main">
					<div class="fe-big">${money(paid)} <span class="fe-muted">${__("of {0}", [money(total)])}</span></div>
					<div class="fe-bar"><div style="width:${Math.min(pct, 100)}%"></div></div>
					<div class="fe-trio">
						<div><span>${__("Total")}</span><b>${money(total)}</b></div>
						<div><span>${__("Paid")}</span><b class="good">${money(paid)}</b></div>
						<div><span>${__("Balance")}</span><b class="${balance ? "bad" : ""}">${money(balance)}</b></div>
					</div>
				</div>
			</div>
		</section>`;

	const step = (label, when, done, icon) => `
		<div class="fe-step ${done ? "done" : ""}"><span class="fe-step-dot">${frappe.utils.icon(icon, "sm")}</span>
		<b>${label}</b><span class="fe-muted">${when ? date(when) : "&nbsp;"}</span></div>`;
	const journey = `
		<section class="fe-card">
			<header><span class="fe-ico">${frappe.utils.icon("graduation-cap", "sm")}</span><div><h5>${__("Student Journey")}</h5><span class="fe-muted">${__("Enrollment milestones")}</span></div></header>
			<div class="fe-journey">
				${step(__("Enrolled"), e.date, true, "clipboard-check")}
				<span class="fe-step-line ${e.joined_on ? "done" : ""}"></span>
				${step(__("Joined"), e.joined_on, !!e.joined_on, "school")}
				<span class="fe-step-line ${e.status === "Completed" ? "done" : ""}"></span>
				${step(__("Completed"), null, e.status === "Completed", "trophy")}
			</div>
			<div class="fe-tags">
				${e.discount ? `<span class="fe-chip good">${__("Discount")}: ${money(c.discount)}</span>` : ""}
				${e.hostel ? `<span class="fe-chip">${frappe.utils.icon("bed-double", "xs")} ${esc(e.hostel)}${e.hostel_type ? " · " + esc(e.hostel_type) : ""}</span>` : ""}
			</div>
		</section>`;

	const extra = (icon, label, sub, value) => `
		<div class="fe-extra"><span class="fe-ico">${frappe.utils.icon(icon, "sm")}</span><div><b>${label}</b><span class="fe-muted">${sub}</span></div><b class="fe-extra-val">${money(value)}</b></div>`;
	const extras = `
		<section class="fe-card">
			<header><span class="fe-ico">${frappe.utils.icon("package", "sm")}</span><div><h5>${__("Additional Charges")}</h5><span class="fe-muted">${__("Transport · Tablet · Deposit · Refund")}</span></div></header>
			${extra("bus", __("Transportation Fee"), __("Total transport paid"), x.transport)}
			${extra("tablet-smartphone", __("Tablet Fee"), __("Total tablet fee paid"), x.tablet)}
			${extra("shield-check", __("Caution Deposit"), __("Refundable"), x.caution)}
			${extra("undo-2", __("Refunded Amount"), __("Total amount refunded"), x.refunded)}
		</section>`;

	const payments = d.payments.length
		? `<div class="fe-table-wrap"><table class="fe-table"><thead><tr>
			<th>${__("Payment")}</th><th>${__("Category")}</th><th>${__("Item")}</th><th class="num">${__("Amount")}</th><th>${__("Mode")}</th><th>${__("Date")}</th></tr></thead><tbody>
			${d.payments
				.map(
					(p) => `<tr><td><a href="/desk/payment-approval-log/${encodeURIComponent(p.log)}">${esc(p.log)}</a></td>
				<td>${esc(p.category)}</td><td>${esc(p.item)}</td><td class="num">${money(p.amount)}</td>
				<td>${esc(p.mode || "")}</td><td>${date(p.date)}</td></tr>`
				)
				.join("")}</tbody></table></div>`
		: `<div class="fe-empty">${__("No approved payments yet")}</div>`;

	return `
		${alert}
		<section class="fe-card fe-head">
			<div class="fe-avatar">${s.image ? `<img src="${esc(s.image)}" alt="">` : initials}</div>
			<div class="fe-who">
				<div class="fe-name">${esc(s.student_name || s.id)}</div>
				<div class="fe-muted fe-mono">${[s.id, s.student_mobile_number, s.student_email_id].filter(Boolean).map(esc).join(" · ")}</div>
				<div class="fe-chips">${chips}</div>
			</div>
			<div class="fe-meta">
				<div><span>${__("Enrollment")}</span><b class="fe-mono">${esc(e.name)}</b></div>
				<div><span>${__("Date")}</span><b>${date(e.date)}</b></div>
				<div><span>${__("Batch")}</span><b>${esc(e.batch || "—")}</b></div>
			</div>
		</section>
		<div class="fe-tiles">
			${tile(__("Offered"), money(c.offered), c.discount ? __("{0} discount → {1}", [money(c.discount), money(c.total)]) : esc(e.academic_year || ""))}
			${tile(__("Course Paid"), money(c.paid), __("{0}% of total", [c.pct]), "good")}
			${tile(__("Balance"), money(c.balance), c.next_due ? __("Next due {0}", [date(c.next_due.date)]) : __("Course fee due"), c.balance ? "bad" : "")}
			${tile(__("Course Type"), esc(e.program_type || "—"), esc(e.vertical || ""))}
			${tile(__("Hostel Paid"), e.hosteller === "Hosteller" ? money(h.paid) : "—", e.hosteller === "Hosteller" ? __("Bal: {0}", [money(h.balance)]) : __("Day scholar"))}
		</div>
		<div class="fe-grid">
			${progress(__("Course Fee"), __("Payment progress"), c.total, c.paid, c.balance, c.pct, "credit-card")}
			${journey}
			${e.hosteller === "Hosteller" ? progress(esc(e.hostel || __("Hostel")), __("Hostel fee summary"), h.total, h.paid, h.balance, h.pct, "bed-double") : ""}
			${extras}
		</div>
		<div class="fe-grid">
			${money_card(__("Discount & Concessions"), "percent", d.discounts, [__("Request"), __("Discount"), __("Amount"), __("Status")],
				(r) => [link("discount-approval-log", r.name), esc(r.discount_id || r.base_of_discount || ""), money(r.amount), chip(r.discount_status)], __("No discount requests"))}
			${money_card(__("Refunds & Transfers"), "undo-2", [...d.refunds.map((r) => ({ ...r, _t: "refund" })), ...d.transfers.map((t) => ({ ...t, _t: "transfer" })), ...d.pending_transfers.map((t) => ({ ...t, _t: "pending" }))],
				[__("Document"), __("What"), __("Amount"), __("Status")],
				(r) => r._t === "refund"
					? [link("fee-refund-request", r.name), esc(__("Refund of {0}", [r.category])), money(-r.amount), chip(r.status)]
					: r._t === "pending"
					? [link("fee-transfer-request", r.name), esc(`${r.from_category} → ${r.to_category}`), money(r.amount), chip("Waiting")]
					: [link("fee-transfer-request", r.name), esc(`${__(r.kind)}: ${r.category}`), money(r.amount), chip("Approved")],
				__("No refunds or transfers"))}
		</div>
		${d.tablets.length ? money_card(__("Tablet"), "tablet-smartphone", d.tablets, [__("Tablet ID"), __("Model"), __("Allocated"), __("Returned")],
			(t) => [esc(t.tablet_id), esc(t.model || ""), date(t.allocated_on), t.returned_on ? date(t.returned_on) : chip("With student")], "") : ""}
		<section class="fe-card"><header><span class="fe-ico">${frappe.utils.icon("receipt", "sm")}</span><div><h5>${__("Payments")}</h5><span class="fe-muted">${__("Approved payments, newest first")}</span></div></header>${payments}</section>`;
}

function fe360_styles() {
	if (document.getElementById("fe360-styles")) return;
	const css = `
.fe-360 { --fe-blue:#2a78d6; --fe-blue-soft:rgba(42,120,214,.12); --fe-good:#0f7a48; --fe-good-bg:rgba(27,175,122,.13);
	--fe-bad:#c62a2f; --fe-bad-bg:rgba(227,73,72,.12); --fe-warn:#a35f00; --fe-warn-bg:rgba(237,161,0,.14);
	padding: 12px 0 4px; display:flex; flex-direction:column; gap:12px; }
[data-theme="dark"] .fe-360 { --fe-blue:#3987e5; --fe-blue-soft:rgba(57,135,229,.18); --fe-good:#4cc38a; --fe-good-bg:rgba(76,195,138,.15);
	--fe-bad:#f08585; --fe-bad-bg:rgba(230,103,103,.16); --fe-warn:#f0b84a; --fe-warn-bg:rgba(201,133,0,.2); }
.fe-loading, .fe-empty { color: var(--text-muted); font-size: var(--text-sm); padding: 18px; text-align:center; }
.fe-alert { display:flex; align-items:center; justify-content:flex-start; gap:8px; padding: 10px 14px; border-radius: 10px; font-size: var(--text-sm); }
.fe-alert .icon { stroke: currentColor; margin:0; flex-shrink:0; }
.fe-alert > span { flex:1; text-align:left; }
.fe-alert.warn { background: var(--fe-warn-bg); color: var(--fe-warn); } .fe-alert.bad { background: var(--fe-bad-bg); color: var(--fe-bad); }
.fe-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 16px 18px; min-width:0; }
.fe-card header { display:flex; align-items:center; gap:10px; margin-bottom: 14px; }
.fe-card header > div { flex:1; min-width:0; display:flex; flex-direction:column; }
.fe-card h5 { margin:0; font-size: var(--text-base); font-weight:600; color: var(--heading-color, var(--text-color)); }
.fe-ico { width:32px; height:32px; border-radius:8px; background: var(--fe-blue-soft); color: var(--fe-blue); display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; }
.fe-ico .icon { stroke: currentColor; }
.fe-muted { color: var(--text-muted); font-size: var(--text-xs); }
.fe-mono { font-family: var(--font-family-monospace, monospace); }
.fe-head { display:flex; gap:16px; align-items:center; flex-wrap: wrap; }
.fe-avatar { width:56px; height:56px; border-radius:14px; background: linear-gradient(135deg,#2a78d6,#1c5cab); color:#fff; font-weight:700; font-size:20px; display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0; }
.fe-avatar img { width:100%; height:100%; object-fit:cover; }
.fe-who { flex:1; min-width: 220px; }
.fe-name { font-size: 18px; font-weight: 700; color: var(--heading-color, var(--text-color)); }
.fe-chips, .fe-tags { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
.fe-chip { display:inline-flex; align-items:center; gap:4px; font-size: var(--text-xs); font-weight:600; padding: 2px 9px; border-radius: 999px; background: var(--control-bg); color: var(--text-color); }
.fe-chip .icon { stroke: currentColor; }
.fe-chip.info { background: var(--fe-blue-soft); color: var(--fe-blue); } .fe-chip.good { background: var(--fe-good-bg); color: var(--fe-good); }
.fe-chip.bad { background: var(--fe-bad-bg); color: var(--fe-bad); } .fe-chip.warn { background: var(--fe-warn-bg); color: var(--fe-warn); }
.fe-meta { display:flex; gap: 22px; padding-left: 18px; border-left: 1px solid var(--border-color); }
.fe-meta div { display:flex; flex-direction:column; } .fe-meta span { font-size: 10px; letter-spacing:.06em; text-transform: uppercase; color: var(--text-muted); }
.fe-meta b { font-size: var(--text-sm); color: var(--text-color); }
.fe-tiles { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:12px; }
.fe-tile { background: var(--card-bg); border:1px solid var(--border-color); border-radius:12px; padding: 12px 14px; box-shadow: inset 0 3px 0 var(--fe-blue); }
.fe-tile.good { box-shadow: inset 0 3px 0 var(--fe-good); } .fe-tile.bad { box-shadow: inset 0 3px 0 var(--fe-bad); }
.fe-label { font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--text-muted); }
.fe-value { font-size: 20px; font-weight: 700; margin: 4px 0 2px; font-variant-numeric: tabular-nums; color: var(--heading-color, var(--text-color)); }
.fe-tile.good .fe-value { color: var(--fe-good); } .fe-tile.bad .fe-value { color: var(--fe-bad); }
.fe-foot { font-size: var(--text-xs); color: var(--text-muted); }
.fe-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.fe-progress { display:flex; gap:18px; align-items:center; }
.fe-ring { width: 84px; height: 84px; flex-shrink:0; }
.fe-ring-track { fill:none; stroke: var(--control-bg); stroke-width: 8; }
.fe-ring-bar { fill:none; stroke: var(--fe-blue); stroke-width: 8; stroke-linecap: round; }
.fe-ring-pct { font-size: 17px; font-weight: 700; fill: var(--text-color); } .fe-ring-sub { font-size: 9px; fill: var(--text-muted); text-transform: uppercase; }
.fe-progress-main { flex:1; min-width:0; }
.fe-big { font-size: 22px; font-weight: 700; color: var(--fe-blue); font-variant-numeric: tabular-nums; }
.fe-big .fe-muted { font-weight: 400; }
.fe-bar { height: 8px; background: var(--control-bg); border-radius: 4px; margin: 10px 0 12px; overflow:hidden; }
.fe-bar div { height:100%; background: var(--fe-blue); border-radius: 4px; }
.fe-trio { display:grid; grid-template-columns: repeat(3,1fr); gap:8px; }
.fe-trio div { background: var(--control-bg); border-radius: 8px; padding: 6px 10px; display:flex; flex-direction:column; }
.fe-trio span { font-size: 10px; text-transform: uppercase; letter-spacing:.05em; color: var(--text-muted); }
.fe-trio b { font-variant-numeric: tabular-nums; color: var(--text-color); white-space:nowrap; font-size: var(--text-sm); } .fe-trio b.good { color: var(--fe-good); } .fe-trio b.bad { color: var(--fe-bad); }
.fe-journey { display:flex; align-items:flex-start; justify-content:space-between; padding: 6px 4px 10px; }
.fe-step { display:flex; flex-direction:column; align-items:center; gap:4px; text-align:center; min-width: 76px; color: var(--text-muted); }
.fe-step b { font-size: var(--text-sm); }
.fe-step-dot { width: 44px; height: 44px; border-radius: 50%; border: 2px solid var(--border-color); display:flex; align-items:center; justify-content:center; background: var(--control-bg); }
.fe-step-dot .icon { stroke: currentColor; }
.fe-step.done { color: var(--fe-blue); } .fe-step.done .fe-step-dot { border-color: var(--fe-blue); background: var(--fe-blue-soft); }
.fe-step-line { flex:1; height:2px; background: var(--border-color); margin-top: 22px; } .fe-step-line.done { background: var(--fe-blue); }
.fe-extra { display:flex; align-items:center; gap:12px; padding: 10px 0; border-top: 1px solid var(--border-color); }
.fe-extra > div { flex:1; display:flex; flex-direction:column; } .fe-extra b { font-size: var(--text-sm); color: var(--text-color); }
.fe-extra-val { font-variant-numeric: tabular-nums; }
.fe-table-wrap { overflow-x:auto; }
.fe-table { width:100%; border-collapse: collapse; font-size: var(--text-sm); }
.fe-table th { color: var(--text-muted); font-weight:500; text-align:left; padding: 6px 10px; border-bottom: 1px solid var(--border-color); white-space:nowrap; }
.fe-table td { padding: 8px 10px; border-bottom: 1px solid var(--border-color); white-space:nowrap; color: var(--text-color); }
.fe-table .num { text-align:right; font-variant-numeric: tabular-nums; }
@media (max-width: 1100px) { .fe-tiles { grid-template-columns: repeat(3, minmax(0,1fr)); } }
@media (max-width: 800px) { .fe-grid { grid-template-columns: 1fr; } .fe-meta { border-left:0; padding-left:0; } .fe-tiles { grid-template-columns: 1fr 1fr; } }
`;
	const el = document.createElement("style");
	el.id = "fe360-styles";
	el.textContent = css;
	document.head.appendChild(el);
}
