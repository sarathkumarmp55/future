// Shared clickable tile strip for list views (Lead, Opportunity).
// Tiles and counts come from future.list_tiles.get_tile_counts(doctype, filters):
// counts follow the list's own filters; clicking a tile applies its filters,
// clicking again clears them. A "Created" quick filter sits above the tiles.

const LIST_TILE_PERIODS = [
	["", __("Any time")],
	["today", __("Today")],
	["this week", __("This week")],
	["this month", __("This month")],
	["last month", __("Last month")],
	["this year", __("This year")],
];

class FutureListTiles {
	constructor(listview, doctype) {
		this.listview = listview;
		this.doctype = doctype;
		this.data = null;
		future_list_tile_styles();
		this.$wrap = $(`<div class="lt-wrap">
			<div class="lt-bar">
				<div class="lt-period" role="group" aria-label="${__("Created")}"></div>
				<span class="lt-hint">${__("Click a tile to filter the list. Click again to clear.")}</span>
			</div>
			<div class="lt-tiles"></div>
		</div>`);
		listview.page.main.find(".lt-wrap").remove();
		listview.$frappe_list.before(this.$wrap);
		this.render_periods();
		this.schedule = frappe.utils.debounce(() => this.load(), 250);
		this.schedule();
	}

	filters() {
		return this.listview.filter_area ? this.listview.get_filters_for_args() : [];
	}

	load() {
		frappe
			.xcall("future.list_tiles.get_tile_counts", { doctype: this.doctype, filters: this.filters() })
			.then((d) => {
				this.data = d;
				this.render();
			});
	}

	field_filters(fieldname) {
		return this.filters().filter((f) => f[1] === fieldname);
	}

	active_key() {
		if (!this.data) return "all";
		const owned = this.data.owned_fields;
		const current = this.filters().filter((f) => owned.includes(f[1]));
		if (!current.length) return "all";
		const sig = (fs, dynamic) =>
			JSON.stringify(
				fs
					.map((f) => [f[1], f[2], dynamic && !Array.isArray(f[3]) ? "" : Array.isArray(f[3]) ? [...f[3]].sort() : f[3]])
					.sort()
			);
		for (const t of this.data.tiles) {
			const own = t.filters.filter((f) => owned.includes(f[1]));
			if (own.length && sig(own, t.dynamic) === sig(current, t.dynamic)) return t.key;
		}
		return null;
	}

	async apply(key) {
		const fa = this.listview.filter_area;
		const active = this.active_key();
		for (const field of this.data.owned_fields) await fa.remove(field);
		const tile = this.data.tiles.find((t) => t.key === key);
		if (tile && tile.filters.length && key !== active) await fa.add(tile.filters);
	}

	render() {
		const active = this.active_key();
		this.$wrap.find(".lt-tiles").html(
			this.data.tiles
				.map(
					(t) => `<button type="button" class="lt-tile ${t.tone || ""} ${active === t.key ? "active" : ""}"
					data-key="${t.key}" aria-pressed="${active === t.key}">
					<span class="lt-label">${frappe.utils.escape_html(t.label)}</span>
					<span class="lt-value">${format_number(t.count, null, 0)}</span>
					<span class="lt-foot">${frappe.utils.escape_html(t.foot)}</span>
				</button>`
				)
				.join("")
		);
		this.$wrap.find(".lt-tile").on("click", (e) => this.apply($(e.currentTarget).attr("data-key")));
		this.render_periods();
	}

	render_periods() {
		const current = (this.field_filters("creation")[0] || [])[3];
		const span = this.field_filters("creation")[0]?.[2] === "Timespan" ? current : current ? "custom" : "";
		this.$wrap.find(".lt-period").html(
			LIST_TILE_PERIODS.map(
				([value, label]) =>
					`<button type="button" class="lt-chip ${span === value ? "active" : ""}" data-value="${value}">${label}</button>`
			).join("") + (span === "custom" ? `<span class="lt-chip active">${__("Custom")}</span>` : "")
		);
		this.$wrap.find(".lt-chip[data-value]").on("click", async (e) => {
			const value = $(e.currentTarget).attr("data-value");
			const fa = this.listview.filter_area;
			await fa.remove("creation");
			if (value) await fa.add([[this.doctype, "creation", "Timespan", value]]);
		});
	}
}

function future_list_tile_styles() {
	if (document.getElementById("future-list-tile-styles")) return;
	const css = `
.lt-wrap { --lt-blue:#2a78d6; --lt-blue-soft:rgba(42,120,214,.10); --lt-good:#0f7a48; --lt-bad:#c62a2f; --lt-bad-soft:rgba(227,73,72,.10); --lt-warn:#a35f00;
	padding: 12px 15px 4px; }
[data-theme="dark"] .lt-wrap { --lt-blue:#3987e5; --lt-blue-soft:rgba(57,135,229,.16); --lt-good:#4cc38a; --lt-bad:#f08585; --lt-bad-soft:rgba(230,103,103,.14); --lt-warn:#f0b84a; }
.lt-bar { display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; margin-bottom:10px; }
.lt-period { display:flex; gap:4px; flex-wrap:wrap; }
.lt-chip { border:1px solid var(--border-color); background: var(--card-bg); color: var(--text-muted); border-radius: 999px;
	padding: 3px 11px; font-size: var(--text-xs); font-weight:500; cursor:pointer; }
.lt-chip:hover { color: var(--text-color); }
.lt-chip.active { background: var(--text-color); border-color: var(--text-color); color: var(--card-bg); }
.lt-hint { color: var(--text-muted); font-size: var(--text-xs); }
.lt-tiles { display:grid; grid-template-columns: repeat(auto-fit, minmax(128px, 1fr)); gap:10px; }
.lt-tile { text-align:left; background: var(--card-bg); border:1px solid var(--border-color); border-radius: 12px;
	padding: 11px 13px; cursor:pointer; display:flex; flex-direction:column; gap:2px; transition: border-color .12s, box-shadow .12s; min-width:0; }
.lt-tile:hover { border-color: var(--lt-blue); }
.lt-tile:focus-visible { outline: 2px solid var(--lt-blue); outline-offset: 2px; }
.lt-tile.active { border-color: var(--lt-blue); box-shadow: inset 0 3px 0 var(--lt-blue); background: var(--lt-blue-soft); }
.lt-label { font-size: var(--text-xs); color: var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.lt-value { font-size: 22px; font-weight: 650; color: var(--heading-color, var(--text-color)); font-variant-numeric: tabular-nums; letter-spacing:-.01em; }
.lt-foot { font-size: 11px; color: var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.lt-tile.good .lt-value { color: var(--lt-good); }
.lt-tile.alert .lt-value { color: var(--lt-bad); } .lt-tile.alert { background: var(--lt-bad-soft); }
.lt-tile.alert.active { box-shadow: inset 0 3px 0 var(--lt-bad); border-color: var(--lt-bad); }
.lt-tile.warn .lt-value { color: var(--lt-warn); }
@media (max-width: 640px) { .lt-tiles { grid-template-columns: repeat(2, minmax(0,1fr)); } .lt-hint { display:none; } }
`;
	const el = document.createElement("style");
	el.id = "future-list-tile-styles";
	el.textContent = css;
	document.head.appendChild(el);
}
