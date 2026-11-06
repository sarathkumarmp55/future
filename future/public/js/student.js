// Student form: enrollment fee summary (links to each enrollment's 360 view)
// and a quick "Log Mentor Call" action.

frappe.ui.form.on("Student", {
	refresh(frm) {
		render_student_dashboard(frm);
		if (!frm.is_new()) {
			frm.add_custom_button(__("Log Mentor Call"), () => log_mentor_call(frm));
		}
	},
});

function log_mentor_call(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Log a call with {0}", [frm.doc.student_name]),
		fields: [
			{ fieldname: "call_with", fieldtype: "Select", label: __("Spoke To"), options: ["Student", "Parent", "Both"], default: "Student" },
			{ fieldname: "call_type", fieldtype: "Select", label: __("About"), options: ["Academic", "Attendance", "Fee", "Hostel", "Wellbeing", "Other"], default: "Academic" },
			{ fieldname: "outcome", fieldtype: "Select", label: __("Outcome"), options: ["Connected", "Not Reachable", "Call Back Later"], default: "Connected" },
			{ fieldname: "duration_minutes", fieldtype: "Int", label: __("Duration (min)") },
			{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes"), reqd: 1 },
		],
		primary_action_label: __("Save Call"),
		primary_action(v) {
			frm.add_child("custom_mentor_calls", {
				...v,
				call_time: frappe.datetime.now_datetime(),
				mentor: frappe.session.user,
			});
			frm.save().then(() => {
				d.hide();
				frappe.show_alert({ message: __("Call logged"), indicator: "green" });
			});
		},
	});
	d.show();
}

function render_student_dashboard(frm) {
	const control = frm.fields_dict.custom_student_dashboard;
	if (!control || frm.is_new()) return;
	const money = (v) => format_currency(v || 0, null, 0);
	const esc = (v) => frappe.utils.escape_html(v || "");

	frappe.db
		.get_list("Program Enrollment", {
			filters: { student: frm.doc.name, docstatus: ["<", 2] },
			fields: [
				"name", "program", "academic_year", "custom_admission_status", "custom_final_amount",
				"custom_course_paid", "custom_course_balance", "custom_total_hostel_fee", "custom_hostel_paid",
				"custom_hostel_balance", "custom_transport_paid", "custom_hosteller", "custom_hostel",
			],
			order_by: "enrollment_date desc",
		})
		.then((rows) => {
			const bar = (label, total, paid, balance) => {
				const pct = total ? Math.min(100, Math.round((paid * 100) / total)) : 0;
				return `<div class="sd-line">
					<div class="sd-line-head"><span>${label}</span><span class="sd-muted">${pct}% · ${money(paid)} / ${money(total)}</span></div>
					<div class="sd-bar"><div style="width:${pct}%"></div></div>
					${balance ? `<div class="sd-bal">${__("Balance {0}", [money(balance)])}</div>` : ""}
				</div>`;
			};
			const cards = rows.length
				? rows
						.map(
							(e) => `<a class="sd-card" href="/desk/program-enrollment/${encodeURIComponent(e.name)}">
					<div class="sd-head"><b>${esc(e.program)}</b><span class="sd-chip">${esc(__(e.custom_admission_status || "Pending"))}</span></div>
					<div class="sd-muted">${esc(e.academic_year)} · ${esc(e.name)}</div>
					${bar(__("Course fee"), e.custom_final_amount, e.custom_course_paid, e.custom_course_balance)}
					${e.custom_hosteller === "Hosteller" ? bar(__("Hostel fee"), e.custom_total_hostel_fee, e.custom_hostel_paid, e.custom_hostel_balance) : ""}
					${e.custom_transport_paid ? `<div class="sd-muted">${__("Transport paid {0}", [money(e.custom_transport_paid)])}</div>` : ""}
					<div class="sd-open">${__("Open full view")} →</div>
				</a>`
						)
						.join("")
				: `<div class="sd-muted">${__("No program enrollment yet.")}</div>`;
			control.html(`<div class="sd-wrap">${cards}</div>`);
		});
	student_dashboard_styles();
}

function student_dashboard_styles() {
	if (document.getElementById("sd-styles")) return;
	const el = document.createElement("style");
	el.id = "sd-styles";
	el.textContent = `
.sd-wrap { display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:12px; }
.sd-card { display:flex; flex-direction:column; gap:8px; padding:14px 16px; border:1px solid var(--border-color); border-radius:12px;
	background: var(--card-bg); color: var(--text-color); text-decoration:none; }
.sd-card:hover { border-color: var(--primary, #2a78d6); text-decoration:none; color: var(--text-color); }
.sd-head { display:flex; justify-content:space-between; gap:8px; align-items:center; }
.sd-chip { font-size: var(--text-xs); font-weight:600; padding: 2px 9px; border-radius: 999px; background: var(--control-bg); }
.sd-muted { color: var(--text-muted); font-size: var(--text-xs); }
.sd-line-head { display:flex; justify-content:space-between; font-size: var(--text-sm); }
.sd-bar { height:8px; background: var(--control-bg); border-radius:4px; overflow:hidden; margin-top:4px; }
.sd-bar div { height:100%; background: #2a78d6; border-radius:4px; }
[data-theme="dark"] .sd-bar div { background: #3987e5; }
.sd-bal { font-size: var(--text-xs); color: #c62a2f; margin-top:2px; }
[data-theme="dark"] .sd-bal { color: #f08585; }
.sd-open { font-size: var(--text-xs); color: var(--text-muted); }
`;
	document.head.appendChild(el);
}
