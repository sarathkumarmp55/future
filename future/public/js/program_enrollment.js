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

function render_360(d) {
	const e = d.enrollment, s = d.student, c = d.course, h = d.hostel, x = d.extras;
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));
	const money = (v) => format_currency(v || 0, null, 0);
	const date = (v) => (v ? frappe.datetime.str_to_user(v) : "—");
	const ico = (name, size = "sm") => frappe.utils.icon(name, size);
	const initials = (s.student_name || "?").split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
	const is_hosteller = e.hosteller === "Hosteller";

	// fee status chip, as in the PDF ("Pending" next to "Joined")
	const fee_status = c.balance <= 0 && c.total ? ["Fees Paid", "good"] : c.paid > 0 ? ["Part Paid", "warn"] : ["Payment Pending", "warn"];
	const adm_tone = { Pending: "warn", Joined: "teal", Completed: "indigo", Dropped: "bad", Cancelled: "bad" }[e.status] || "";
	const chip = (text, tone = "", dot = false) => `<span class="fe-chip ${tone}">${dot ? '<i class="fe-dot"></i>' : ""}${esc(text)}</span>`;
	const status_chip = (status) => chip(__(status || ""), { Approved: "good", Paid: "good", Pending: "warn", Requested: "warn", Waiting: "warn", Rejected: "bad", Cancelled: "bad" }[status] || "");
	const link = (route, name) => `<a href="/desk/${route}/${encodeURIComponent(name)}">${esc(name)}</a>`;

	const alert = d.overdue
		? `<div class="fe-alert bad">${ico("triangle-alert")}<span><b>${__("Overdue")}</b> ${__("{0} past its due date", [money(d.overdue)])}</span></div>`
		: c.balance
		? `<div class="fe-alert warn">${ico("triangle-alert")}<span><b>${__("Outstanding Balance")}</b> ${__("{0} pending on course fee", [money(c.balance)])}${
				c.next_due ? ` · ${__("next {0} on {1}", [money(c.next_due.amount), date(c.next_due.date)])}` : ""
		  }</span></div>`
		: "";

	const header = `
		<section class="fe-card fe-head">
			<div class="fe-avatar">${s.image ? `<img src="${esc(s.image)}" alt="">` : initials}</div>
			<div class="fe-who">
				<div class="fe-name">${esc(s.student_name || s.id)}</div>
				<div class="fe-mono fe-muted">${[s.id, s.student_mobile_number, s.student_email_id].filter(Boolean).map(esc).join(" · ")}</div>
				<div class="fe-chips">
					${chip(__(fee_status[0]), fee_status[1], true)}
					${chip(__(e.status || "Pending"), adm_tone, true)}
					${e.program ? chip(e.program, "indigo") : ""}
					${e.center ? chip(e.center) : ""}
					${e.vertical || e.academic_year ? chip([e.vertical, e.academic_year].filter(Boolean).join(" · ")) : ""}
					${e.program_type ? chip(e.program_type, "teal", true) : ""}
				</div>
			</div>
			<div class="fe-meta">
				<div><span>${__("Enrollment")}</span><b class="fe-mono">${esc(e.name)}</b></div>
				<div><span>${__("Date")}</span><b class="fe-mono">${esc(e.date || "")}</b></div>
				<div><span>${__("Batch")}</span><b class="fe-mono">${esc(e.batch || "—")}</b></div>
			</div>
		</section>`;

	const tile = (accent, icon, label, value, foot, value_tone = "") => `
		<div class="fe-tile" style="--acc: var(--fe-${accent})">
			<span class="fe-tile-ico">${ico(icon)}</span>
			<div class="fe-label">${label}</div>
			<div class="fe-value ${value_tone}">${value}</div>
			<div class="fe-foot">${foot}</div>
		</div>`;
	const tiles = `
		<div class="fe-tiles">
			${tile("indigo", "target", __("Offered"), money(c.offered), c.discount ? __("{0} discount", [money(c.discount)]) : esc(e.academic_year || ""))}
			${tile("green", "circle-check", __("Course Paid"), money(c.paid), __("{0}% of total", [c.pct]), "green")}
			${tile("red", "hourglass", __("Balance"), money(c.balance), c.next_due ? __("Next due {0}", [date(c.next_due.date)]) : __("Course fee due"), c.balance ? "red" : "")}
			${tile("violet", "clipboard-list", __("Course Type"), esc(e.vertical || e.program_type || "—"), esc([e.program_type, e.vertical].filter(Boolean).join(" · ")), "text")}
			${tile("teal", "house", __("Hostel Paid"), is_hosteller ? money(h.paid) : "—", is_hosteller ? __("Bal: {0}", [money(h.balance)]) : __("Day scholar"), "teal")}
		</div>`;

	const fee_card = (accent, icon, title, sub, total, paid, balance, pct, labels, footer) => `
		<section class="fe-card fe-accent" style="--acc: var(--fe-${accent})">
			<header>
				<span class="fe-ico">${ico(icon)}</span>
				<div><h5>${title}</h5><span class="fe-muted">${sub}</span></div>
				<span class="fe-chip soft">${__("{0}% collected", [pct])}</span>
			</header>
			<div class="fe-progress">
				<div class="fe-pct"><b>${pct}<small>%</small></b><span>${__("Paid")}</span></div>
				<div class="fe-progress-main">
					<div class="fe-big">${money(paid)}</div>
					<div class="fe-muted">${__("of {0} total", [money(total)])}</div>
					<div class="fe-bar"><div style="width:${Math.min(pct, 100)}%"></div></div>
					<div class="fe-trio">
						<div><span>${labels[0]}</span><b class="acc">${money(total)}</b></div>
						<div><span>${__("Paid")}</span><b class="green">${money(paid)}</b></div>
						<div><span>${__("Balance")}</span><b class="${balance ? "red" : ""}">${money(balance)}</b></div>
					</div>
				</div>
			</div>
			${footer ? `<footer class="fe-card-foot ${balance ? "warn" : "good"}">${ico(balance ? "triangle-alert" : "circle-check", "xs")}<span>${footer}</span><span class="fe-chip ${balance ? "warn" : "good"}">${__("{0}% paid", [pct])}</span></footer>` : ""}
		</section>`;

	const course_card = fee_card("indigo", "credit-card", __("Course Fee"), __("Payment Progress"), c.total, c.paid, c.balance, c.pct,
		[__("Offered")], c.balance ? __("Balance Outstanding") : __("Course fee fully paid"));
	const hostel_card = is_hosteller
		? fee_card("teal", "house", esc(e.hostel || __("Hostel")), __("Hostel Fee Summary"), h.total, h.paid, h.balance, h.pct,
			[__("Total")], h.balance ? __("{0} pending", [money(h.balance)]) : __("Hostel fee fully paid"))
		: "";

	const step = (label, when, done, icon, tag) => `
		<div class="fe-step ${done ? "done" : ""}">
			<span class="fe-step-dot">${ico(icon)}</span>
			<b>${label}</b>
			<span class="fe-muted fe-mono">${when ? esc(when) : "&nbsp;"}</span>
			${tag || ""}
		</div>`;
	const arrow = (done) => `<span class="fe-arrow ${done ? "done" : ""}">${ico("arrow-right")}</span>`;
	const journey = `
		<section class="fe-card fe-accent" style="--acc: var(--fe-indigo)">
			<header><span class="fe-ico">${ico("graduation-cap")}</span><div><h5>${__("Student Journey")}</h5><span class="fe-muted">${__("Enrollment milestones")}</span></div></header>
			<div class="fe-journey">
				${step(__("Enrolled"), e.date, true, "clipboard-list", e.discount ? chip(__("Discount"), "green") : "")}
				${arrow(!!e.joined_on)}
				${step(__("Joined"), e.joined_on, !!e.joined_on, "graduation-cap", e.hostel ? chip(__("Hostel"), "teal") : "")}
				${arrow(e.status === "Completed")}
				${step(__("Completed"), null, e.status === "Completed", "trophy")}
			</div>
		</section>`;

	const extra = (accent, icon, label, sub, value) => `
		<div class="fe-extra" style="--acc: var(--fe-${accent})">
			<span class="fe-ico">${ico(icon)}</span>
			<div><b>${label}</b><span class="fe-muted">${sub}</span></div>
			<b class="fe-extra-val ${value ? "acc" : "fe-muted"}">${money(value)}</b>
		</div>`;
	const extras = `
		<section class="fe-card fe-accent fe-rainbow">
			<header><span class="fe-ico" style="--acc: var(--fe-orange)">${ico("package")}</span><div><h5>${__("Additional Charges")}</h5><span class="fe-muted">${__("Transport · Tablet · Refund")}</span></div></header>
			${extra("orange", "bus", __("Transportation Fee"), __("Total transport paid"), x.transport)}
			${extra("violet", "tablet-smartphone", __("Tablet Fee"), __("Total tab fee paid"), x.tablet)}
			${extra("teal", "shield-check", __("Caution Deposit"), __("Refundable"), x.caution)}
			${extra("pink", "undo-2", __("Refunded Amount"), __("Total amount refunded"), x.refunded)}
		</section>`;

	const table_card = (accent, icon, title, rows, headers, cells, empty) => `
		<section class="fe-card fe-accent" style="--acc: var(--fe-${accent})">
			<header><span class="fe-ico">${ico(icon)}</span><div><h5>${title}</h5></div></header>
			${rows.length
				? `<div class="fe-table-wrap"><table class="fe-table"><thead><tr>${headers.map((hd, i) => `<th class="${i === 2 ? "num" : ""}">${hd}</th>`).join("")}</tr></thead>
					<tbody>${rows.map((r) => `<tr>${cells(r).map((v, i) => `<td class="${i === 2 ? "num" : ""}">${v}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
				: `<div class="fe-empty">${empty}</div>`}
		</section>`;

	const discounts = table_card("green", "percent", __("Discount & Concessions"), d.discounts,
		[__("Request"), __("Discount"), __("Amount"), __("Status")],
		(r) => [link("discount-approval-log", r.name), esc(r.discount_id || r.base_of_discount || ""), money(r.amount), status_chip(r.discount_status)],
		__("No discount requests"));
	const moves = [...d.refunds.map((r) => ({ ...r, _t: "refund" })), ...d.transfers.map((t) => ({ ...t, _t: "transfer" })), ...d.pending_transfers.map((t) => ({ ...t, _t: "pending" }))];
	const refunds = table_card("pink", "undo-2", __("Refunds & Transfers"), moves,
		[__("Document"), __("What"), __("Amount"), __("Status")],
		(r) => r._t === "refund"
			? [link("fee-refund-request", r.name), esc(__("Refund of {0}", [r.category])), money(-r.amount), status_chip(r.status)]
			: r._t === "pending"
			? [link("fee-transfer-request", r.name), esc(`${r.from_category} → ${r.to_category}`), money(r.amount), status_chip("Waiting")]
			: [link("fee-transfer-request", r.name), esc(`${__(r.kind)}: ${r.category}`), money(r.amount), status_chip("Approved")],
		__("No refunds or transfers"));
	const tablets = d.tablets.length
		? table_card("violet", "tablet-smartphone", __("Tablet"), d.tablets, [__("Tablet ID"), __("Model"), __("Allocated"), __("Returned")],
			(t) => [esc(t.tablet_id), esc(t.model || ""), date(t.allocated_on), t.returned_on ? date(t.returned_on) : chip(__("With student"), "teal")], "")
		: "";
	const payments = table_card("indigo", "receipt", __("Payments"), d.payments,
		[__("Payment"), __("Category"), __("Amount"), __("Item"), __("Mode"), __("Date")],
		(p) => [link("payment-approval-log", p.log), esc(p.category), money(p.amount), esc(p.item), esc(p.mode || ""), date(p.date)],
		__("No approved payments yet"));

	return `
		<div class="fe-toolbar">
			<button type="button" class="btn btn-sm fe-dl-png">${ico("image", "xs")} ${__("Download PNG")}</button>
			<button type="button" class="btn btn-sm fe-dl-pdf">${ico("file-text", "xs")} ${__("Download PDF")}</button>
		</div>
		<div class="fe-sheet">
			${alert}
			${header}
			${tiles}
			<div class="fe-grid">
				<div class="fe-col">${course_card}${hostel_card}</div>
				<div class="fe-col">${journey}${extras}</div>
			</div>
			<div class="fe-grid">${discounts}${refunds}</div>
			${tablets}
			${payments}
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
	--fe-indigo:#4f46e5; --fe-green:#059669; --fe-red:#dc2626; --fe-violet:#7c3aed; --fe-teal:#0d9488;
	--fe-orange:#ea580c; --fe-pink:#db2777; --fe-warn:#b45309; --fe-warn-bg:#fffbeb; --fe-warn-line:#fde68a;
	--fe-bad-bg:#fef2f2; --fe-bad-line:#fecaca; --fe-sheet:#f1f5f9;
	padding: 12px 0 4px;
}
[data-theme="dark"] .fe-360 {
	--fe-indigo:#818cf8; --fe-green:#34d399; --fe-red:#f87171; --fe-violet:#a78bfa; --fe-teal:#2dd4bf;
	--fe-orange:#fb923c; --fe-pink:#f472b6; --fe-warn:#fbbf24; --fe-warn-bg:rgba(251,191,36,.10); --fe-warn-line:rgba(251,191,36,.30);
	--fe-bad-bg:rgba(248,113,113,.10); --fe-bad-line:rgba(248,113,113,.30); --fe-sheet:rgba(255,255,255,.03);
}
.fe-loading, .fe-empty { color: var(--text-muted); font-size: var(--text-sm); padding: 18px; text-align:center; }
.fe-toolbar { display:flex; justify-content:flex-end; gap:8px; margin-bottom:10px; }
.fe-toolbar .btn { display:inline-flex; align-items:center; gap:6px; font-weight:600; }
.fe-dl-png { background: var(--fe-indigo); color:#fff; border-color: var(--fe-indigo); }
.fe-dl-png:hover { color:#fff; opacity:.92; }
.fe-dl-pdf { background: var(--card-bg); color: var(--fe-red); border: 1px solid var(--fe-bad-line); }
.fe-toolbar .icon { stroke: currentColor; }
.fe-sheet { background: var(--fe-sheet); border-radius: 16px; padding: 14px; display:flex; flex-direction:column; gap:12px; }
.fe-alert { display:flex; align-items:center; gap:10px; padding: 11px 16px; border-radius: 12px; font-size: var(--text-sm); border:1px solid; }
.fe-alert .icon { stroke: currentColor; margin:0; flex-shrink:0; }
.fe-alert > span { flex:1; text-align:left; }
.fe-alert.warn { background: var(--fe-warn-bg); color: var(--fe-warn); border-color: var(--fe-warn-line); }
.fe-alert.bad { background: var(--fe-bad-bg); color: var(--fe-red); border-color: var(--fe-bad-line); }
.fe-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 14px; padding: 16px 18px; min-width:0; position:relative; overflow:hidden; }
.fe-accent { border-top: 3px solid var(--acc); }
.fe-rainbow { border-top: 0; } .fe-rainbow::before { content:""; position:absolute; inset:0 0 auto 0; height:3px; background: linear-gradient(90deg, var(--fe-orange), var(--fe-pink), var(--fe-violet)); }
.fe-card header { display:flex; align-items:center; gap:12px; margin-bottom: 14px; }
.fe-card header > div { flex:1; min-width:0; display:flex; flex-direction:column; }
.fe-card h5 { margin:0; font-size: var(--text-base); font-weight:700; color: var(--heading-color, var(--text-color)); }
.fe-ico { width:36px; height:36px; border-radius:10px; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0;
	color: var(--acc, var(--fe-indigo)); background: color-mix(in srgb, var(--acc, var(--fe-indigo)) 13%, transparent); }
.fe-ico .icon { stroke: currentColor; }
.fe-muted { color: var(--text-muted); font-size: var(--text-xs); }
.fe-mono { font-family: var(--font-family-monospace, ui-monospace, monospace); }
.fe-head { display:flex; gap:18px; align-items:center; flex-wrap: wrap;
	background: linear-gradient(110deg, var(--card-bg) 55%, color-mix(in srgb, var(--fe-indigo) 6%, var(--card-bg))); }
.fe-avatar { width:60px; height:60px; border-radius:16px; background: linear-gradient(135deg,#2563eb,#4f46e5); color:#fff; font-weight:700; font-size:20px;
	display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0; }
.fe-avatar img { width:100%; height:100%; object-fit:cover; }
.fe-who { flex:1; min-width: 240px; }
.fe-name { font-size: 18px; font-weight: 800; letter-spacing:.01em; text-transform: uppercase; color: var(--heading-color, var(--text-color)); }
.fe-chips { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
.fe-chip { display:inline-flex; align-items:center; gap:5px; font-size: 11px; font-weight:600; padding: 2px 9px; border-radius: 999px;
	background: var(--control-bg); color: var(--text-color); border: 1px solid var(--border-color); white-space:nowrap; }
.fe-dot { width:6px; height:6px; border-radius:50%; background: currentColor; display:inline-block; }
.fe-chip.warn { background: var(--fe-warn-bg); color: var(--fe-warn); border-color: var(--fe-warn-line); }
.fe-chip.good, .fe-chip.green { background: color-mix(in srgb, var(--fe-green) 12%, transparent); color: var(--fe-green); border-color: color-mix(in srgb, var(--fe-green) 30%, transparent); }
.fe-chip.teal { background: color-mix(in srgb, var(--fe-teal) 12%, transparent); color: var(--fe-teal); border-color: color-mix(in srgb, var(--fe-teal) 30%, transparent); }
.fe-chip.indigo { background: color-mix(in srgb, var(--fe-indigo) 10%, transparent); color: var(--fe-indigo); border-color: color-mix(in srgb, var(--fe-indigo) 28%, transparent); }
.fe-chip.bad { background: var(--fe-bad-bg); color: var(--fe-red); border-color: var(--fe-bad-line); }
.fe-chip.soft { background: color-mix(in srgb, var(--acc) 10%, transparent); color: var(--acc); border-color: color-mix(in srgb, var(--acc) 30%, transparent); }
.fe-meta { display:flex; gap: 26px; padding-left: 20px; border-left: 1px solid var(--border-color); }
.fe-meta div { display:flex; flex-direction:column; gap:3px; }
.fe-meta span { font-size: 10px; letter-spacing:.1em; text-transform: uppercase; color: var(--text-muted); text-align:center; }
.fe-meta b { font-size: var(--text-sm); color: var(--text-color); }
.fe-tiles { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:12px; }
.fe-tile { background: var(--card-bg); border:1px solid var(--border-color); border-top: 3px solid var(--acc); border-radius:14px; padding: 14px 16px; }
.fe-tile-ico { width:28px; height:28px; border-radius:8px; display:inline-flex; align-items:center; justify-content:center; margin-bottom:8px;
	color: var(--acc); background: color-mix(in srgb, var(--acc) 13%, transparent); }
.fe-tile-ico .icon { stroke: currentColor; }
.fe-label { font-size: 10px; letter-spacing: .09em; text-transform: uppercase; color: var(--text-muted); font-weight:600; }
.fe-value { font-size: 20px; font-weight: 800; margin: 3px 0 2px; font-family: var(--font-family-monospace, ui-monospace, monospace); color: var(--heading-color, var(--text-color)); }
.fe-value.text { font-family: inherit; font-size: 17px; padding-top: 3px; }
.fe-value.green { color: var(--fe-green); } .fe-value.red { color: var(--fe-red); } .fe-value.teal { color: var(--fe-teal); }
.fe-foot { font-size: var(--text-xs); color: var(--text-muted); }
.fe-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items:start; }
.fe-col { display:flex; flex-direction:column; gap:12px; min-width:0; }
.fe-progress { display:flex; gap:18px; align-items:center; }
.fe-pct { width:64px; text-align:center; flex-shrink:0; display:flex; flex-direction:column; }
.fe-pct b { font-size: 22px; font-weight:800; color: var(--acc); } .fe-pct small { font-size: 12px; }
.fe-pct span { font-size: 10px; letter-spacing:.08em; text-transform: uppercase; color: var(--text-muted); }
.fe-progress-main { flex:1; min-width:0; }
.fe-big { font-size: 26px; font-weight: 800; color: var(--acc); font-family: var(--font-family-monospace, ui-monospace, monospace); line-height:1.1; }
.fe-bar { height:8px; background: var(--control-bg); border-radius:4px; margin: 10px 0 12px; overflow:hidden; }
.fe-bar div { height:100%; border-radius:4px; background: linear-gradient(90deg, var(--acc), color-mix(in srgb, var(--acc) 60%, #22d3ee)); }
.fe-trio { display:grid; grid-template-columns: repeat(3,1fr); gap:8px; }
.fe-trio div { background: var(--control-bg); border:1px solid var(--border-color); border-radius: 10px; padding: 6px 10px; display:flex; flex-direction:column; }
.fe-trio span { font-size: 10px; text-transform: uppercase; letter-spacing:.06em; color: var(--text-muted); font-weight:600; }
.fe-trio b { font-family: var(--font-family-monospace, ui-monospace, monospace); font-size: var(--text-sm); white-space:nowrap; color: var(--text-color); }
.fe-trio b.acc, .fe-extra-val.acc { color: var(--acc); } .fe-trio b.green { color: var(--fe-green); } .fe-trio b.red { color: var(--fe-red); }
.fe-card-foot { display:flex; align-items:center; gap:8px; margin: 14px -18px -16px; padding: 10px 18px; font-size: var(--text-sm); font-weight:600; border-top:1px solid var(--border-color); }
.fe-card-foot > span:first-of-type { flex:1; }
.fe-card-foot .icon { stroke: currentColor; }
.fe-card-foot.warn { background: var(--fe-warn-bg); color: var(--fe-warn); }
.fe-card-foot.good { background: color-mix(in srgb, var(--fe-green) 8%, transparent); color: var(--fe-green); }
.fe-journey { display:flex; align-items:flex-start; justify-content:space-around; padding: 6px 4px 6px; gap:4px; }
.fe-step { display:flex; flex-direction:column; align-items:center; gap:4px; text-align:center; min-width: 90px; color: var(--text-muted); }
.fe-step b { font-size: var(--text-sm); }
.fe-step-dot { width: 48px; height: 48px; border-radius: 50%; border: 2px solid var(--border-color); display:flex; align-items:center; justify-content:center;
	background: var(--control-bg); color: var(--text-muted); }
.fe-step-dot .icon { stroke: currentColor; }
.fe-step.done { color: var(--fe-indigo); }
.fe-step.done .fe-step-dot { border-color: var(--fe-indigo); background: color-mix(in srgb, var(--fe-indigo) 10%, var(--card-bg)); color: var(--fe-indigo); }
.fe-arrow { margin-top: 14px; color: var(--border-color); } .fe-arrow.done { color: var(--fe-indigo); }
.fe-arrow .icon { stroke: currentColor; }
.fe-extra { display:flex; align-items:center; gap:12px; padding: 11px 0; border-top: 1px solid var(--border-color); }
.fe-extra > div { flex:1; display:flex; flex-direction:column; } .fe-extra b { font-size: var(--text-sm); color: var(--text-color); }
.fe-extra-val { font-family: var(--font-family-monospace, ui-monospace, monospace); font-size: 16px !important; }
.fe-table-wrap { overflow-x:auto; }
.fe-table { width:100%; border-collapse: collapse; font-size: var(--text-sm); }
.fe-table th { color: var(--text-muted); font-weight:600; text-align:left; padding: 7px 10px; border-bottom: 1px solid var(--border-color); white-space:nowrap;
	font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }
.fe-table td { padding: 8px 10px; border-bottom: 1px solid var(--border-color); white-space:nowrap; color: var(--text-color); }
.fe-table tr:last-child td { border-bottom: 0; }
.fe-table .num { text-align:right; font-family: var(--font-family-monospace, ui-monospace, monospace); }
@media (max-width: 1100px) { .fe-tiles { grid-template-columns: repeat(3, minmax(0,1fr)); } }
@media (max-width: 800px) { .fe-grid { grid-template-columns: 1fr; } .fe-meta { border-left:0; padding-left:0; } .fe-tiles { grid-template-columns: 1fr 1fr; } }
`;
	const el = document.createElement("style");
	el.id = "fe360-styles";
	el.textContent = css;
	document.head.appendChild(el);
}
