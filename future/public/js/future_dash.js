// Shared pieces for the Future desk dashboards (Hostel, Payments), in the same quiet style
// as the Lead Dashboard: Frappe 16 neutrals, one accent (Future blue) on data only, status
// colour only where it means something, figures in a divided strip, no gradients or icon tiles.
window.FutureDash = (function () {
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));
	const money = (v) => format_currency(v || 0, null, 0);
	const int = (v) => format_number(v || 0, null, 0);
	const date = (v) => (v ? frappe.datetime.str_to_user(v) : "—");

	// target: a shadow root (workspace custom block) or nothing for the page itself
	function styles(target) {
		const into = target || document.head;
		if ((target || document).querySelector && (target || document).querySelector("#fd-styles")) return;
		const el = document.createElement("style");
		el.id = "fd-styles";
		el.textContent = `
.fd-root { --fd-accent:#2a78d6; --fd-accent-soft:rgba(42,120,214,.10); --fd-neg:#c4242a; --fd-pos:#247b50;
	--fd-warn-bg:#fffbeb; --fd-warn-ink:#92400e; --fd-neg-bg:#ffedea; --fd-neg-ink:#831c1e; --fd-pos-bg:#dcfae5; --fd-pos-ink:#04250e;
	padding: 6px 16px 40px; display:flex; flex-direction:column; gap:12px; }
[data-theme="dark"] .fd-root, :host-context([data-theme="dark"]) .fd-root { --fd-accent:#5598e7; --fd-accent-soft:rgba(85,152,231,.14); --fd-neg:#e5566f; --fd-pos:#3fc07a;
	--fd-warn-bg:#2a2412; --fd-warn-ink:#f0c060; --fd-neg-bg:#2c1a20; --fd-neg-ink:#e5566f; --fd-pos-bg:#172a1d; --fd-pos-ink:#3fc07a; }
.fd-root.fd-loading { opacity:.55; pointer-events:none; }
.fd-sub { color: var(--text-muted); font-size: 13px; }
.fd-strip { display:grid; background: var(--card-bg); border:1px solid var(--border-color); border-radius:8px; overflow:hidden; }
.fd-fig { display:flex; flex-direction:column; gap:2px; padding: 14px 18px; border-left:1px solid var(--border-color); min-width:0; text-align:left;
	background: transparent; border-top:0; border-right:0; border-bottom:0; color: var(--text-color); }
.fd-fig:first-child { border-left:0; }
button.fd-fig { cursor:pointer; } button.fd-fig:hover { background: var(--control-bg); }
.fd-fig-label { font-size: 13px; color: var(--text-muted); }
.fd-fig-value { font-size: 22px; font-weight: 500; color: var(--heading-color, var(--text-color)); font-variant-numeric: tabular-nums; letter-spacing:-.01em; white-space:nowrap; }
.fd-fig.lead .fd-fig-value { font-size: 30px; font-weight: 600; }
.fd-fig.neg .fd-fig-value { color: var(--fd-neg); }
.fd-fig-note { font-size: 12px; color: var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.fd-grid { display:grid; gap:12px; align-items:start; }
.fd-card { background: var(--card-bg); border:1px solid var(--border-color); border-radius:8px; padding: 16px 20px; min-width:0; }
.fd-card-head { display:flex; justify-content:space-between; align-items:baseline; gap:12px; margin-bottom: 12px; }
.fd-card h5 { margin:0; font-size:15px; font-weight:600; color: var(--heading-color, var(--text-color)); }
.fd-link { font-size: 13px; color: var(--text-muted); } .fd-link:hover { color: var(--text-color); }
.fd-empty { color: var(--text-muted); font-size: 13px; margin: 4px 0; }
.fd-table { width:100%; border-collapse:collapse; font-size:13px; }
.fd-table th { font-size:12px; font-weight:400; color: var(--text-muted); text-align:left; padding: 0 8px 8px; white-space:nowrap; }
.fd-table td { padding: 9px 8px; border-top:1px solid color-mix(in srgb, var(--border-color) 60%, transparent); color: var(--text-color); white-space:nowrap; }
.fd-table th:first-child, .fd-table td:first-child { padding-left:0; } .fd-table th:last-child, .fd-table td:last-child { padding-right:0; }
.fd-table .num { text-align:right; font-variant-numeric: tabular-nums; }
.fd-table td.fd-wrap { white-space: normal; }
.fd-table tr.fd-dim td { color: var(--text-muted); }
.fd-meter b { font-size: 13px; }
.fd-table tr.fd-click { cursor:pointer; } .fd-table tr.fd-click:hover td { background: var(--control-bg); }
.fd-meter { display:flex; align-items:center; gap:8px; min-width: 120px; }
.fd-meter-track { flex:1; height:6px; background: var(--control-bg); border-radius:3px; overflow:hidden; }
.fd-meter-track span { display:block; height:100%; background: var(--fd-accent); border-radius:3px; }
.fd-meter.full .fd-meter-track span { background: var(--fd-neg); }
.fd-meter b { font-weight:500; width: 42px; text-align:right; font-variant-numeric: tabular-nums; }
.fd-pill { display:inline-flex; align-items:center; height:20px; padding:0 8px; border-radius:999px; font-size:11.5px; font-weight:500; background: var(--control-bg); color: var(--text-color); }
.fd-pill.pos { background: var(--fd-pos-bg); color: var(--fd-pos-ink); } .fd-pill.neg { background: var(--fd-neg-bg); color: var(--fd-neg-ink); }
.fd-pill.warn { background: var(--fd-warn-bg); color: var(--fd-warn-ink); }
.fd-queue { list-style:none; margin:0; padding:0; }
.fd-queue li { display:flex; justify-content:space-between; align-items:center; padding: 10px 0; border-top:1px solid color-mix(in srgb, var(--border-color) 60%, transparent); cursor:pointer; font-size:13px; }
.fd-queue li:first-child { border-top:0; padding-top:2px; }
.fd-queue li:hover span:first-child { text-decoration: underline; }
.fd-queue b { font-size:16px; font-weight:600; font-variant-numeric: tabular-nums; }
.fd-queue li.zero b { color: var(--text-muted); font-weight:400; }
.fd-bars { display:flex; flex-direction:column; gap:9px; }
.fd-bar-row { display:grid; grid-template-columns: minmax(80px, 34%) 1fr auto; gap:10px; align-items:center; font-size:13px; }
.fd-bar-row .fd-meter-track { height:8px; }
.fd-bar-row > span:last-child { font-variant-numeric: tabular-nums; text-align:right; }
.fd-chart svg { display:block; overflow: visible; }
.fd-grid-line { stroke: var(--border-color); stroke-width:1; }
.fd-axis { fill: var(--text-muted); font-size: 11px; }
.fd-line { fill:none; stroke: var(--fd-accent); stroke-width:2; stroke-linejoin:round; stroke-linecap:round; }
.fd-area { fill: var(--fd-accent-soft); }
.fd-cross { stroke: var(--text-muted); stroke-dasharray: 3 3; }
.fd-dot { fill: var(--fd-accent); stroke: var(--card-bg); stroke-width:2; }
.fd-tip { position: fixed; z-index: 1100; pointer-events:none; opacity:0; transform: translate(-50%, calc(-100% - 10px));
	background: var(--card-bg); color: var(--text-color); border:1px solid var(--border-color); box-shadow: var(--shadow-md);
	border-radius: 6px; padding: 6px 10px; font-size: 12px; white-space:nowrap; }
.fd-tip.show { opacity:1; }
@media (max-width: 1000px) { .fd-grid { grid-template-columns: 1fr !important; } .fd-strip { grid-template-columns: 1fr 1fr !important; }
	.fd-fig:nth-child(odd) { border-left:0; } .fd-fig:nth-child(n+3) { border-top:1px solid var(--border-color); } }
`;
		into.appendChild(el);
	}

	const fig = (label, value, note, cls = "", attrs = "") =>
		`<${attrs ? "button type=\"button\"" : "div"} class="fd-fig ${cls}" ${attrs}><span class="fd-fig-label">${label}</span>` +
		`<span class="fd-fig-value">${value}</span><span class="fd-fig-note">${note || "&nbsp;"}</span></${attrs ? "button" : "div"}>`;
	const strip = (figs, cols) => `<section class="fd-strip" style="grid-template-columns:${cols || `repeat(${figs.length}, minmax(0,1fr))`}">${figs.join("")}</section>`;
	const card = (title, body, aside = "") => `<section class="fd-card"><div class="fd-card-head"><h5>${title}</h5>${aside}</div>${body}</section>`;
	const meter = (pct, full) => `<span class="fd-meter ${full ? "full" : ""}"><span class="fd-meter-track"><span style="width:${Math.min(pct, 100)}%"></span></span><b>${pct}%</b></span>`;
	const pill = (text, tone = "") => `<span class="fd-pill ${tone}">${esc(text)}</span>`;
	const empty = (text) => `<p class="fd-empty">${text}</p>`;

	function bars(rows, fmt = int) {
		if (!rows.length) return empty(__("No data in this period"));
		const max = Math.max(...rows.map((r) => r.n), 1);
		return `<div class="fd-bars">${rows
			.map((r) => `<div class="fd-bar-row"><span>${esc(r.label)}</span><span class="fd-meter-track"><span style="width:${Math.max((r.n / max) * 100, 2)}%"></span></span><span>${fmt(r.n)}</span></div>`)
			.join("")}</div>`;
	}

	function tip() {
		let $t = $(".fd-tip");
		if (!$t.length) $t = $(`<div class="fd-tip"></div>`).appendTo(document.body);
		return $t;
	}

	// One series, 2px line, faint area, three gridlines, crosshair tooltip.
	function line($box, pts, { value = "amount", fmt = money, label = __("Amount") } = {}) {
		const W = Math.max($box.width(), 280), H = 200, m = { t: 10, r: 10, b: 24, l: 56 };
		const iw = W - m.l - m.r, ih = H - m.t - m.b;
		const max = Math.max(...pts.map((p) => p[value]), 1);
		const p10 = Math.pow(10, Math.floor(Math.log10(max)));
		const whole = fmt === int; // counts: whole-number ticks only
		let top = [1, 2, 2.5, 5, 10].map((s) => s * p10).find((v) => v >= max) || max;
		if (whole) top = Math.max(Math.ceil(top), 2);
		const x = (i) => m.l + (pts.length === 1 ? iw / 2 : (i * iw) / (pts.length - 1));
		const y = (v) => m.t + ih - (v / top) * ih;
		const short = (v) => (v >= 100000 ? `${Math.round(v / 1000) / 100}L` : v >= 1000 ? `${Math.round(v / 100) / 10}k` : `${v}`);
		const ticks = whole && top % 2 ? [0, top] : [0, top / 2, top];
		const grid = ticks.map((t) => `<line x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}" class="fd-grid-line"/><text x="${m.l - 8}" y="${y(t) + 4}" text-anchor="end" class="fd-axis">${short(t)}</text>`).join("");
		const step = Math.ceil(pts.length / Math.max(Math.floor(iw / 70), 1));
		const xl = pts.map((p, i) => ((i % step === 0 && pts.length - 1 - i >= step * 0.6) || i === pts.length - 1)
			? `<text x="${x(i)}" y="${H - 4}" text-anchor="middle" class="fd-axis">${frappe.datetime.str_to_obj(p.date).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</text>` : "").join("");
		const path = pts.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p[value])}`).join(" ");
		$box.html(`<svg width="${W}" height="${H}" role="img" aria-label="${esc(label)}">${grid}${xl}
			<path d="${path} L${x(pts.length - 1)},${y(0)} L${x(0)},${y(0)} Z" class="fd-area"/><path d="${path}" class="fd-line"/>
			<line class="fd-cross" y1="${m.t}" y2="${m.t + ih}" style="display:none"/><circle class="fd-dot" r="4.5" style="display:none"/>
			<rect x="${m.l}" y="${m.t}" width="${iw}" height="${ih}" fill="transparent" class="fd-hit"/></svg>`);
		const $svg = $box.find("svg"), cross = $svg.find(".fd-cross")[0], dot = $svg.find(".fd-dot")[0], $t = tip();
		$svg.find(".fd-hit").on("mousemove", (e) => {
			const r = $svg[0].getBoundingClientRect();
			const i = Math.min(pts.length - 1, Math.max(0, Math.round(((e.clientX - r.left - m.l) / iw) * (pts.length - 1))));
			cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.style.display = "";
			dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(pts[i][value])); dot.style.display = "";
			$t.html(`<b>${date(pts[i].date)}</b><br>${esc(label)}: ${fmt(pts[i][value])}`).css({ left: r.left + x(i), top: r.top + y(pts[i][value]) }).addClass("show");
		}).on("mouseleave", () => { cross.style.display = "none"; dot.style.display = "none"; $t.removeClass("show"); });
	}

	return { esc, money, int, date, styles, fig, strip, card, meter, pill, empty, bars, line };
})();
