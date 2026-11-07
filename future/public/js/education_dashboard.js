// Education overview, shown at the top of the Education home (a workspace custom block,
// "Future Education Overview", added by future.setup.education_home on migrate).
// Same quiet style as the Lead / Admissions / Hostel / Payments dashboards (future_dash.js).
window.FutureEducation = {
	mount(root) {
		const host = root.querySelector("#future-education");
		if (!host) return;
		FutureDash.styles(root); // inside the block
		FutureDash.styles(); // the page, for the chart tooltip
		host.innerHTML = `<div class="fd-root"><p class="fd-sub">${__("Loading…")}</p></div>`;
		frappe
			.xcall("future.dashboards.education_dashboard")
			.then((d) => this.render(host, d))
			.catch(() => (host.innerHTML = `<div class="fd-root"><p class="fd-sub">${__("The overview is for staff with Education access.")}</p></div>`));
	},

	render(host, d) {
		const D = FutureDash, k = d.kpis;
		const att_note = k.marked_today
			? __("{0} present, {1} absent", [D.int(k.present_today), D.int(k.absent_today)])
			: __("not marked yet today");
		const strip = D.strip([
			D.fig(__("Active students"), D.int(k.active), __("{0} joined since {1}", [D.int(k.new_this_year), D.date(d.year_start)]), "lead", 'data-go="students"'),
			D.fig(__("Attendance today"), k.marked_today ? `${k.rate_today}%` : "—", att_note, k.marked_today && k.rate_today < 75 ? "neg" : "", 'data-go="attendance"'),
			D.fig(__("Programmes"), D.int(k.running), __("with students enrolled"), "", 'data-go="programmes"'),
			D.fig(__("Student groups"), D.int(k.groups), __("batches and classes"), "", 'data-go="groups"'),
			D.fig(__("Instructors"), D.int(k.instructors), __("active"), "", 'data-go="instructors"'),
		], "1.2fr 1fr 1fr 1fr 1fr");

		const groups = d.groups.length
			? `<table class="fd-table"><thead><tr><th>${__("Group")}</th><th>${__("Programme")}</th><th>${__("Instructors")}</th><th class="num">${__("Students")}</th></tr></thead><tbody>
				${d.groups.map((g) => `<tr class="fd-click" data-group="${D.esc(g.name)}"><td>${D.esc(g.student_group_name || g.name)}</td>
				<td class="fd-wrap">${D.esc(g.program || "")}</td><td class="fd-wrap">${g.instructors ? D.esc(g.instructors) : '<span class="fd-sub">none assigned</span>'}</td>
				<td class="num">${g.max_strength ? `${g.students} / ${g.max_strength}` : g.students}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("No student groups yet. Create them from Student Group."));

		const low = d.low_attendance.length
			? `<table class="fd-table"><tbody>${d.low_attendance.map((r) => `<tr class="fd-click" data-student="${D.esc(r.student)}">
				<td class="fd-wrap">${D.esc(r.student_name)}<div class="fd-sub">${__("{0} of {1} days present", [r.present, r.marked])}</div></td>
				<td class="num">${D.pill(`${r.rate}%`, "neg")}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("No student is under 75% attendance in the last 30 days."));

		const recent = d.recent.length
			? `<table class="fd-table"><tbody>${d.recent.map((r) => `<tr class="fd-click" data-student="${D.esc(r.name)}">
				<td class="fd-wrap">${D.esc(r.student_name)}<div class="fd-sub">${D.esc(r.custom_program || "")}</div></td>
				<td class="num">${D.date(r.joining_date)}</td></tr>`).join("")}</tbody></table>`
			: D.empty(__("No students yet."));

		host.innerHTML = `<div class="fd-root" style="padding: 4px 0 8px">
			${strip}
			<div class="fd-grid" style="grid-template-columns: minmax(0,1.25fr) minmax(0,1fr)">
				<div class="fd-grid">
					${D.card(__("Attendance, last 14 days"), `<div class="fd-chart"></div>`, `<span class="fd-sub">${__("% present each day")}</span>`)}
					${D.card(__("Student groups"), groups, `<a class="fd-link" data-go="groups">${__("All")} →</a>`)}
					${D.card(__("Students by programme"), D.bars(d.programs))}
				</div>
				<div class="fd-grid">
					${D.card(__("Below 75% attendance"), low, `<span class="fd-sub">${__("last 30 days")}</span>`)}
					${D.card(__("Students by centre"), D.bars(d.centers))}
					${D.card(__("Recently joined"), recent, `<a class="fd-link" data-go="students">${__("All")} →</a>`)}
				</div>
			</div>
		</div>`;

		const chart = host.querySelector(".fd-chart");
		if (d.attendance.some((a) => a.marked)) {
			FutureDash.line($(chart), d.attendance, { value: "rate", fmt: (v) => `${v}%`, label: __("Present") });
		} else {
			chart.innerHTML = FutureDash.empty(__("No attendance marked in the last 14 days."));
		}

		const list = (doctype, options) => {
			frappe.route_options = options || {};
			frappe.set_route("List", doctype);
		};
		const go = {
			students: () => list("Student", { enabled: 1 }),
			attendance: () => list("Student Attendance", { date: frappe.datetime.get_today() }),
			programmes: () => frappe.set_route("admissions-dashboard"),
			groups: () => list("Student Group", { disabled: 0 }),
			instructors: () => list("Instructor"),
		};
		host.querySelectorAll("[data-go]").forEach((el) => el.addEventListener("click", () => go[el.dataset.go]()));
		host.querySelectorAll("[data-group]").forEach((el) => el.addEventListener("click", () => frappe.set_route("Form", "Student Group", el.dataset.group)));
		host.querySelectorAll("[data-student]").forEach((el) => el.addEventListener("click", () => frappe.set_route("Form", "Student", el.dataset.student)));
	},
};
