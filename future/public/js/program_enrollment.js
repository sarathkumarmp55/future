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
			.then((d) => {
				$box.html(render_360(d));
				fe360_bind_export($box, `${frm.doc.student_name || frm.doc.student} - ${frm.doc.name}`);
			});

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

// The 360 view answers one question first: what does this student owe, and are they on time?
// One accent (the Future blue) on the data only: progress bars and the next instalment.
// Colour elsewhere means status: red overdue, green paid, amber due soon. Figures are tabular.
function render_360(d) {
	const e = d.enrollment, s = d.student, c = d.course, h = d.hostel, x = d.extras;
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));
	const money = (v) => format_currency(v || 0, null, 0);
	const date = (v) => (v ? frappe.datetime.str_to_user(v) : "—");
	const is_hosteller = e.hosteller === "Hosteller";
	const initials = (s.student_name || "?").split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
	const link = (route, name) => `<a href="/desk/${route}/${encodeURIComponent(name)}">${esc(name)}</a>`;

	const PILL = {
		Paid: "pos", Approved: "pos", Joined: "pos", Completed: "pos", "Fees paid": "pos",
		Overdue: "neg", Rejected: "neg", Cancelled: "neg", Dropped: "neg",
		"Partly Paid": "warn", Requested: "warn", Waiting: "warn", Pending: "warn", "Part paid": "warn", "Payment pending": "warn",
	};
	const pill = (text) => `<span class="fe-pill ${PILL[text] || ""}">${esc(__(text))}</span>`;
	const fee_state = c.total && c.balance <= 0 ? "Fees paid" : d.overdue ? "Overdue" : c.paid > 0 ? "Part paid" : "Payment pending";

	// ---- notice: only when something needs doing
	const notice = d.overdue
		? `<div class="fe-notice neg"><b>${money(d.overdue)} ${__("overdue")}</b><span>${__("An instalment is past its due date. Collect it or agree a new date with the parent.")}</span></div>`
		: c.next_due && c.balance
		? `<div class="fe-notice"><b>${__("Next instalment {0} on {1}", [money(c.next_due.amount), date(c.next_due.date)])}</b><span>${__("{0} of the course fee is still to be paid.", [money(c.balance)])}</span></div>`
		: "";

	// ---- who
	const meta_line = [e.program, e.center, [e.program_type, e.vertical].filter(Boolean).join(" · "), e.academic_year].filter(Boolean).map(esc).join(" · ");
	const header = `
		<section class="fe-card fe-head">
			<div class="fe-avatar">${s.image ? `<img src="${esc(s.image)}" alt="">` : esc(initials)}</div>
			<div class="fe-who">
				<div class="fe-name-row"><h4 class="fe-name">${esc(s.student_name || s.id)}</h4>${pill(e.status || "Pending")}${fee_state === "Fees paid" ? pill(fee_state) : ""}</div>
				<div class="fe-line">${meta_line}</div>
				<div class="fe-line fe-muted">${[s.id, s.student_mobile_number, s.student_email_id].filter(Boolean).map(esc).join(" · ")}</div>
			</div>
			<dl class="fe-facts">
				<div><dt>${__("Enrollment")}</dt><dd>${esc(e.name)}</dd></div>
				<div><dt>${__("Enrolled on")}</dt><dd>${date(e.date)}</dd></div>
				<div><dt>${__("Batch")}</dt><dd>${esc(e.batch || "Not assigned")}</dd></div>
			</dl>
		</section>`;

	// ---- the figures: one strip, the balance leads
	const fig = (label, value, note, cls = "") => `
		<div class="fe-fig ${cls}"><span class="fe-fig-label">${label}</span><span class="fe-fig-value">${value}</span><span class="fe-fig-note">${note}</span></div>`;
	const strip = `
		<section class="fe-card fe-strip">
			${fig(__("Balance due"), money(c.balance),
				d.overdue ? __("{0} of it overdue", [money(d.overdue)])
				: c.next_due ? __("Next {0} on {1}", [money(c.next_due.amount), date(c.next_due.date)])
				: c.balance ? "" : __("Nothing due"), `lead ${d.overdue ? "neg" : ""}`)}
			${fig(__("Course fee"), money(c.total), c.discount ? __("{0} offered, {1} discount", [money(c.offered), money(c.discount)]) : __("as offered"))}
			${fig(__("Paid so far"), money(c.paid), __("{0}% of the course fee", [c.pct]))}
			${is_hosteller ? fig(__("Hostel balance"), money(h.balance), __("{0}% of the hostel fee paid", [h.pct])) : fig(__("Hostel"), __("Day scholar"), __("no hostel fee"))}
		</section>`;

	// ---- schedules: the instalments themselves
	const schedule_table = (rows, limit) => {
		if (!rows.length) return `<p class="fe-empty">${__("No schedule yet. Use Fees → Build Default Schedules.")}</p>`;
		const shown = limit ? rows.slice(0, limit) : rows;
		const next = rows.find((r) => r.status !== "Paid");
		return `<table class="fe-table">
			<thead><tr><th>${__("Due")}</th><th>${__("For")}</th><th class="num">${__("Amount")}</th><th class="num">${__("Paid")}</th><th>${__("Status")}</th></tr></thead>
			<tbody>${shown
				.map(
					(r) => `<tr class="${r === next ? "is-next" : ""}">
				<td>${date(r.due_date)}</td><td>${esc(r.label)}</td>
				<td class="num">${money(r.amount)}</td><td class="num">${r.paid ? money(r.paid) : '<span class="fe-muted">—</span>'}</td>
				<td>${pill(r.status)}</td></tr>`
				)
				.join("")}</tbody></table>
			${limit && rows.length > limit ? `<p class="fe-more">${__("{0} more instalments in the Fee Plan tab", [rows.length - limit])}</p>` : ""}`;
	};
	const bar = (pct) => `<div class="fe-bar" role="img" aria-label="${pct}% paid"><span style="width:${Math.min(pct, 100)}%"></span></div>`;
	const course = `
		<section class="fe-card">
			<div class="fe-card-head"><h5>${__("Course fee")}</h5><span class="fe-muted">${__("{0} of {1} paid", [money(c.paid), money(c.total)])}</span></div>
			${bar(c.pct)}
			${schedule_table(d.course_schedule)}
		</section>`;
	const hostel = is_hosteller
		? `<section class="fe-card">
			<div class="fe-card-head"><h5>${__("Hostel fee")}</h5><span class="fe-muted">${esc([e.hostel, e.hostel_type].filter(Boolean).join(" · "))}</span></div>
			<div class="fe-sub">${__("{0} of {1} paid", [money(h.paid), money(h.total)])}</div>
			${bar(h.pct)}
			${schedule_table(d.hostel_schedule, 6)}
		</section>`
		: "";

	// ---- journey: a plain stepper
	const steps = [
		[__("Enrolled"), e.date, true],
		[__("Joined"), e.joined_on, !!e.joined_on],
		[__("Completed"), null, e.status === "Completed"],
	];
	const current = steps.findIndex((st) => !st[2]);
	const journey = `
		<section class="fe-card">
			<div class="fe-card-head"><h5>${__("Journey")}</h5></div>
			<ol class="fe-steps">${steps
				.map(
					([label, when, done], i) => `<li class="${done ? "done" : i === current ? "now" : ""}">
				<span class="fe-step-mark"></span><span class="fe-step-label">${label}</span>
				<span class="fe-muted">${when ? date(when) : i === current ? __("Next step") : ""}</span></li>`
				)
				.join("")}</ol>
			${e.discount || e.hostel ? `<p class="fe-note">${[e.discount ? __("Discount of {0} applied", [money(c.discount)]) : "", e.hostel ? __("Hostel allotted: {0}", [esc(e.hostel)]) : ""].filter(Boolean).join(" · ")}</p>` : ""}
		</section>`;

	// ---- other money: definition rows, no icons
	const row = (label, value, note) => `<div class="fe-row"><dt>${label}${note ? `<span class="fe-muted">${note}</span>` : ""}</dt><dd>${value ? money(value) : '<span class="fe-muted">—</span>'}</dd></div>`;
	const other = `
		<section class="fe-card">
			<div class="fe-card-head"><h5>${__("Other charges")}</h5></div>
			<dl class="fe-rows">
				${row(__("Transportation"), x.transport, __("paid"))}
				${row(__("Tablet"), x.tablet, __("paid"))}
				${row(__("Caution deposit"), x.caution, __("refundable"))}
				${row(__("Refunded"), x.refunded)}
			</dl>
		</section>`;

	const list_card = (title, rows, render, empty) => `
		<section class="fe-card">
			<div class="fe-card-head"><h5>${title}</h5>${rows.length ? `<span class="fe-muted">${rows.length}</span>` : ""}</div>
			${rows.length ? `<ul class="fe-list">${rows.map(render).join("")}</ul>` : `<p class="fe-empty">${empty}</p>`}
		</section>`;
	const discounts = list_card(__("Discounts"), d.discounts,
		(r) => `<li><span>${link("discount-approval-log", r.name)}<span class="fe-muted">${esc(r.discount_id || r.base_of_discount || "")}</span></span><span class="num">${money(r.amount)}</span>${pill(r.discount_status)}</li>`,
		__("No discount requested"));
	const moves = [
		...d.refunds.map((r) => ({ doc: r.name, route: "fee-refund-request", what: __("Refund of {0}", [r.category]), amount: -r.amount, status: r.status })),
		...d.transfers.map((t) => ({ doc: t.name, route: "fee-transfer-request", what: `${__(t.kind)} · ${t.category}`, amount: t.amount, status: "Approved" })),
		...d.pending_transfers.map((t) => ({ doc: t.name, route: "fee-transfer-request", what: `${t.from_category} → ${t.to_category}`, amount: t.amount, status: "Waiting" })),
	];
	const refunds = list_card(__("Refunds and transfers"), moves,
		(m) => `<li><span>${link(m.route, m.doc)}<span class="fe-muted">${esc(m.what)}</span></span><span class="num">${money(m.amount)}</span>${pill(m.status)}</li>`,
		__("None so far"));
	const tablets = d.tablets.length
		? list_card(__("Tablet"), d.tablets,
			(t) => `<li><span>${esc(t.tablet_id)}<span class="fe-muted">${esc(t.model || "")} · ${__("given {0}", [date(t.allocated_on)])}</span></span><span></span>${t.returned_on ? pill("Returned") : pill("With student")}</li>`, "")
		: "";

	const payments = `
		<section class="fe-card">
			<div class="fe-card-head"><h5>${__("Payments received")}</h5><span class="fe-muted">${d.payments.length ? money(d.payments.reduce((a, p) => a + p.amount, 0)) : ""}</span></div>
			${d.payments.length
				? `<table class="fe-table"><thead><tr><th>${__("Date")}</th><th>${__("For")}</th><th class="num">${__("Amount")}</th><th>${__("Mode")}</th><th>${__("Approval")}</th></tr></thead>
				<tbody>${d.payments.map((p) => `<tr><td>${date(p.date)}</td><td>${esc(p.category)}<span class="fe-muted"> · ${esc(p.item)}</span></td>
				<td class="num">${money(p.amount)}</td><td>${esc(p.mode || "")}</td><td>${link(p.route || "payment-approval-log", p.log)}</td></tr>`).join("")}</tbody></table>`
				: `<p class="fe-empty">${__("No approved payments yet")}</p>`}
		</section>`;

	return `
		<div class="fe-toolbar">
			<button type="button" class="btn btn-default btn-sm fe-dl-png">${__("Download PNG")}</button>
			<button type="button" class="btn btn-default btn-sm fe-dl-pdf">${__("Download PDF")}</button>
		</div>
		<div class="fe-sheet">
			${notice}
			${header}
			${strip}
			<div class="fe-grid">
				<div class="fe-col">${course}${hostel}${payments}</div>
				<div class="fe-col">${journey}${other}${discounts}${refunds}${tablets}</div>
			</div>
		</div>`;
}

// ----------------------------------------------------------------------------- export

function fe360_load(src) {
	return new Promise((resolve, reject) => {
		if (document.querySelector(`script[src="${src}"]`)) return resolve();
		const el = document.createElement("script");
		el.src = src;
		el.onload = resolve;
		el.onerror = () => reject(new Error(`Could not load ${src}`));
		document.head.appendChild(el);
	});
}

// Frappe icons are <use href="#icon-x"> pointing at a sprite elsewhere on the page; an exported
// image does not carry that sprite, so copy each symbol's drawing into the icon itself.
function fe360_inline_icons(root) {
	root.querySelectorAll("svg use").forEach((use) => {
		const id = (use.getAttribute("href") || use.getAttribute("xlink:href") || "").replace(/^#/, "");
		const symbol = id && document.getElementById(id);
		const svg = use.closest("svg");
		if (!symbol || !svg) return;
		if (symbol.getAttribute("viewBox") && !svg.getAttribute("viewBox")) svg.setAttribute("viewBox", symbol.getAttribute("viewBox"));
		const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
		g.innerHTML = symbol.innerHTML;
		use.replaceWith(g);
	});
}

async function fe360_png($box) {
	// html-to-image lets the browser render the view (modern CSS colours included), unlike html2canvas
	await fe360_load("https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.js");
	const sheet = $box.find(".fe-sheet")[0];
	fe360_inline_icons(sheet);
	const bg = getComputedStyle(document.body).backgroundColor || "#ffffff";
	const url = await window.htmlToImage.toPng(sheet, { pixelRatio: 2, backgroundColor: bg, cacheBust: true });
	const img = await new Promise((resolve, reject) => {
		const i = new Image();
		i.onload = () => resolve(i);
		i.onerror = reject;
		i.src = url;
	});
	return { url, width: img.width, height: img.height };
}

function fe360_bind_export($box, name) {
	$box.find(".fe-dl-png").on("click", async () => {
		try {
			const { url } = await fe360_png($box);
			const a = document.createElement("a");
			a.download = `${name}.png`;
			a.href = url;
			a.click();
		} catch (err) {
			frappe.msgprint(__("Could not create the image: {0}", [err.message || err]));
		}
	});
	$box.find(".fe-dl-pdf").on("click", async () => {
		try {
			const shot = await fe360_png($box);
			await fe360_load("https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js");
			const { jsPDF } = window.jspdf;
			const pdf = new jsPDF({ orientation: "p", unit: "mm", format: "a4" });
			const w = pdf.internal.pageSize.getWidth() - 16;
			const page_h = pdf.internal.pageSize.getHeight() - 16;
			const h = (shot.height * w) / shot.width;
			// JPEG, embedded once (alias) and shown page by page, keeps the file small
			const canvas = document.createElement("canvas");
			canvas.width = shot.width;
			canvas.height = shot.height;
			const ctx = canvas.getContext("2d");
			ctx.fillStyle = "#ffffff";
			ctx.fillRect(0, 0, canvas.width, canvas.height);
			const img = new Image();
			await new Promise((r) => ((img.onload = r), (img.src = shot.url)));
			ctx.drawImage(img, 0, 0);
			const jpeg = canvas.toDataURL("image/jpeg", 0.85);
			for (let y = 0; y < h; y += page_h) {
				if (y) pdf.addPage();
				pdf.addImage(jpeg, "JPEG", 8, 8 - y, w, h, "fe360-sheet", "FAST");
			}
			pdf.save(`${name}.pdf`);
		} catch (err) {
			frappe.msgprint(__("Could not create the PDF: {0}", [err.message || err]));
		}
	});
}

function fe360_styles() {
	if (document.getElementById("fe360-styles")) return;
	const css = `
.fe-360 {
	/* Frappe 16 neutrals; one accent (the Future logo blue) for data; status as pale pills */
	--fe-accent: #2a78d6; --fe-accent-soft: rgba(42,120,214,.08);
	--fe-pos: #247b50; --fe-pos-bg: #dcfae5; --fe-pos-ink: #04250e;
	--fe-neg: #c4242a; --fe-neg-bg: #ffedea; --fe-neg-ink: #831c1e;
	--fe-warn-bg: #fffbeb; --fe-warn-line: #fde68a; --fe-warn-ink: #92400e;
	--fe-rule: color-mix(in srgb, var(--border-color) 60%, transparent);
	padding: 12px 0 4px;
}
.fe-fig-value, .fe-table td.num, .fe-row dd, .fe-list .num, .fe-card-head .fe-muted { font-variant-numeric: tabular-nums; }
[data-theme="dark"] .fe-360 {
	--fe-accent: #5598e7; --fe-accent-soft: rgba(85,152,231,.12);
	--fe-pos: #3fc07a; --fe-pos-bg: #172a1d; --fe-pos-ink: #3fc07a;
	--fe-neg: #e5566f; --fe-neg-bg: #2c1a20; --fe-neg-ink: #e5566f;
	--fe-warn-bg: #2a2412; --fe-warn-line: #4a3d16; --fe-warn-ink: #f0c060;
}
.fe-loading { color: var(--text-muted); font-size: var(--text-sm); padding: 18px; }
.fe-toolbar { display:flex; justify-content:flex-end; gap:6px; margin-bottom:10px; }
.fe-sheet { display:flex; flex-direction:column; gap:12px; }
.fe-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px 20px; min-width:0; }
.fe-card-head { display:flex; align-items:baseline; justify-content:space-between; gap:12px; margin-bottom: 10px; }
.fe-card h5 { margin:0; font-size: 15px; font-weight: 600; color: var(--heading-color, var(--text-color)); }
.fe-muted { color: var(--text-muted); font-size: 13px; }
.fe-sub { font-size: 13px; color: var(--text-muted); margin-top: -6px; }
.fe-empty { color: var(--text-muted); font-size: 13px; margin: 2px 0 0; }
.fe-note { color: var(--text-muted); font-size: 13px; margin: 12px 0 0; }
.fe-more { color: var(--text-muted); font-size: 12px; margin: 8px 0 0; }

.fe-notice { display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; padding: 10px 16px; border-radius: 8px; font-size: 13px;
	background: var(--fe-warn-bg); border: 1px solid var(--fe-warn-line); color: var(--fe-warn-ink); }
.fe-notice b { font-weight: 600; }
.fe-notice.neg { background: var(--fe-neg-bg); border-color: color-mix(in srgb, var(--fe-neg) 25%, transparent); color: var(--fe-neg-ink); }

.fe-head { display:flex; gap:16px; align-items:center; flex-wrap: wrap; }
.fe-avatar { width:48px; height:48px; border-radius: 50%; background: var(--fe-accent-soft); color: var(--fe-accent); font-weight:600; font-size:16px;
	display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0; }
.fe-avatar img { width:100%; height:100%; object-fit:cover; }
.fe-who { flex:1 1 360px; min-width: 0; display:flex; flex-direction:column; gap:3px; }
.fe-name-row { display:flex; align-items:center; gap:8px; flex-wrap:wrap; row-gap:4px; }
.fe-name-row .fe-pill:first-of-type { margin-left: 4px; }
.fe-name { margin:0; font-size: 18px; font-weight: 600; color: var(--heading-color, var(--text-color)); }
.fe-line { font-size: 13px; color: var(--text-color); }
.fe-facts { display:flex; gap: 24px; margin:0 0 0 auto; }
.fe-facts div { display:flex; flex-direction:column; gap:2px; }
.fe-facts dt { font-size: 12px; font-weight: 400; color: var(--text-muted); }
.fe-facts dd { margin:0; font-size: 13px; color: var(--text-color); }

.fe-pill { display:inline-flex; align-items:center; height: 20px; padding: 0 8px; border-radius: 999px; font-size: 11.5px; font-weight: 500;
	background: var(--control-bg); color: var(--text-color); white-space:nowrap; }
.fe-pill.pos { background: var(--fe-pos-bg); color: var(--fe-pos-ink); }
.fe-pill.neg { background: var(--fe-neg-bg); color: var(--fe-neg-ink); }
.fe-pill.warn { background: var(--fe-warn-bg); color: var(--fe-warn-ink); }

.fe-strip { display:grid; grid-template-columns: 1.3fr 1fr 1fr 1fr; padding: 0; }
.fe-fig { display:flex; flex-direction:column; gap:2px; padding: 14px 20px; border-left: 1px solid var(--border-color); min-width:0; }
.fe-fig:first-child { border-left: 0; }
.fe-fig-label { font-size: 13px; color: var(--text-muted); }
.fe-fig-value { font-size: 22px; font-weight: 500; color: var(--heading-color, var(--text-color)); letter-spacing: -.01em; white-space:nowrap; }
.fe-fig.lead .fe-fig-value { font-size: 30px; font-weight: 600; }
.fe-fig.neg .fe-fig-value { color: var(--fe-neg); }
.fe-fig-note { font-size: 12px; color: var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

.fe-grid { display:grid; grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr); gap: 12px; align-items:start; }
.fe-col { display:flex; flex-direction:column; gap:12px; min-width:0; }
.fe-bar { height: 6px; background: var(--control-bg); border-radius: 3px; margin: 2px 0 14px; overflow:hidden; }
.fe-bar span { display:block; height:100%; background: var(--fe-accent); border-radius: 3px; }

.fe-table { width:100%; border-collapse: collapse; font-size: 13px; }
.fe-table th { font-size: 12px; font-weight: 400; color: var(--text-muted); text-align:left; padding: 0 8px 8px; }
.fe-table td { padding: 8px; border-top: 1px solid var(--fe-rule); color: var(--text-color); white-space:nowrap; }
.fe-table th:first-child, .fe-table td:first-child { padding-left: 0; }
.fe-table th:last-child, .fe-table td:last-child { padding-right: 0; }
.fe-table .num { text-align:right; }
.fe-table tr.is-next td { background: var(--fe-accent-soft); }
.fe-table tr.is-next td:first-child { box-shadow: inset 2px 0 0 var(--fe-accent); padding-left: 8px; }

.fe-steps { list-style:none; margin: 0; padding: 0; display:flex; flex-direction:column; }
.fe-steps li { display:grid; grid-template-columns: 18px 1fr auto; align-items:center; gap: 10px; padding: 7px 0; position:relative; }
.fe-steps li:not(:last-child)::after { content:""; position:absolute; left: 5px; top: 22px; bottom: -8px; width: 1px; background: var(--border-color); }
.fe-step-mark { width: 11px; height: 11px; border-radius: 50%; border: 1.5px solid var(--border-color); background: var(--card-bg); }
.fe-steps li.done .fe-step-mark { background: var(--text-color); border-color: var(--text-color); }
.fe-steps li.now .fe-step-mark { border-color: var(--fe-accent); box-shadow: 0 0 0 3px var(--fe-accent-soft); }
.fe-step-label { font-size: 13px; color: var(--text-color); }
.fe-steps li:not(.done):not(.now) .fe-step-label { color: var(--text-muted); }

.fe-rows { margin:0; display:flex; flex-direction:column; }
.fe-row { display:flex; justify-content:space-between; align-items:baseline; gap:12px; padding: 8px 0; border-top: 1px solid var(--fe-rule); }
.fe-row:first-child { border-top: 0; padding-top: 0; }
.fe-row dt { font-size: 13px; font-weight: 400; color: var(--text-color); display:flex; gap:6px; align-items:baseline; }
.fe-row dd { margin:0; font-size: 13px; color: var(--text-color); }
.fe-list { list-style:none; margin:0; padding:0; }
.fe-list li { display:grid; grid-template-columns: 1fr auto auto; gap: 10px; align-items:center; padding: 8px 0; border-top: 1px solid var(--fe-rule); font-size: 13px; }
.fe-list li:first-child { border-top:0; padding-top:0; }
.fe-list li > span:first-child { display:flex; flex-direction:column; min-width:0; }
.fe-list .num { text-align:right; }

@media (max-width: 1100px) { .fe-grid { grid-template-columns: 1fr; } }
@media (max-width: 720px) {
	.fe-strip { grid-template-columns: 1fr 1fr; }
	.fe-fig:nth-child(3) { border-left: 0; }
	.fe-fig:nth-child(n+3) { border-top: 1px solid var(--border-color); }
	.fe-facts { gap: 18px; }
	.fe-table { display:block; overflow-x:auto; }
}
`;
	const el = document.createElement("style");
	el.id = "fe360-styles";
	el.textContent = css;
	document.head.appendChild(el);
}
