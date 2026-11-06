// Lead list: a strip of clickable tiles above the list.
//
// - Counts follow the list's own filters (future.lead_stages.get_tile_counts,
//   which uses frappe.get_list, so lead privacy always applies).
// - Clicking a tile filters the list to exactly those leads; clicking it again
//   clears that filter. The number on a tile equals the rows it shows.
// - A "Created" quick filter replaces the old From/To date boxes and is a
//   normal list filter, so it shows in the filter bar and can be saved.

frappe.listview_settings["Lead"] = Object.assign(frappe.listview_settings["Lead"] || {}, {
	onload(listview) {
		listview.lead_tiles = new LeadTiles(listview);
	},
	refresh(listview) {
		listview.lead_tiles && listview.lead_tiles.schedule();
	},
});

const LEAD_TILE_ORDER = ["all", "new", "contacted", "interested", "won", "lost", "late"];
const LEAD_PERIODS = [
	["", __("Any time")],
	["today", __("Today")],
	["this week", __("This week")],
	["this month", __("This month")],
	["last month", __("Last month")],
	["this year", __("This year")],
];

class LeadTiles {
	constructor(listview) {
		this.listview = listview;
		this.data = null;
		lead_tile_styles();
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
			.xcall("future.lead_stages.get_tile_counts", { filters: this.filters() })
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
		const current = this.filters().filter((f) => ["status", "custom_assigned_on", "custom_lead_user"].includes(f[1]));
		if (!current.length) return "all";
		const sig = (fs) =>
			JSON.stringify(
				fs.map((f) => [f[1], f[2], Array.isArray(f[3]) ? [...f[3]].sort() : f[3]]).sort()
			);
		const now = sig(current);
		for (const key of LEAD_TILE_ORDER) {
			const t = this.data.tiles[key];
			if (key === "late") {
				// the cut-off time moves, so compare only the field set and statuses
				if (current.some((f) => f[1] === "custom_assigned_on")) return key;
				continue;
			}
			if (t.filters.length && sig(t.filters) === now) return key;
		}
		return null;
	}

	async apply(key) {
		const fa = this.listview.filter_area;
		const active = this.active_key();
		await fa.remove("status");
		await fa.remove("custom_assigned_on");
		await fa.remove("custom_lead_user");
		if (key !== "all" && key !== active) {
			await fa.add(this.data.tiles[key].filters);
		}
	}

	render() {
		const d = this.data;
		const active = this.active_key();
		const foot = {
			all: __("matching the filters"),
			new: __("status still New"),
			contacted: __("trying to reach"),
			interested: __("in discussion"),
			won: __("{0}% conversion", [d.conversion]),
			lost: __("disqualified or lost"),
			late: __("not called within {0}h", [d.sla_hours]),
		};
		const tone = { won: "good", lost: "muted", late: d.counts.late ? "bad" : "muted" };
		this.$wrap.find(".lt-tiles").html(
			LEAD_TILE_ORDER.map(
				(key) => `<button type="button" class="lt-tile ${tone[key] || ""} ${active === key ? "active" : ""}"
					data-key="${key}" aria-pressed="${active === key}">
					<span class="lt-label">${frappe.utils.escape_html(d.tiles[key].label)}</span>
					<span class="lt-value">${format_number(d.counts[key], null, 0)}</span>
					<span class="lt-foot">${foot[key]}</span>
				</button>`
			).join("")
		);
		this.$wrap.find(".lt-tile").on("click", (e) => this.apply($(e.currentTarget).attr("data-key")));
		this.render_periods();
	}

	render_periods() {
		const current = (this.field_filters("creation")[0] || [])[3];
		const span = this.field_filters("creation")[0]?.[2] === "Timespan" ? current : current ? "custom" : "";
		this.$wrap.find(".lt-period").html(
			LEAD_PERIODS.map(
				([value, label]) =>
					`<button type="button" class="lt-chip ${span === value ? "active" : ""}" data-value="${value}">${label}</button>`
			).join("") + (span === "custom" ? `<span class="lt-chip active">${__("Custom")}</span>` : "")
		);
		this.$wrap.find(".lt-chip[data-value]").on("click", async (e) => {
			const value = $(e.currentTarget).attr("data-value");
			const fa = this.listview.filter_area;
			await fa.remove("creation");
			if (value) await fa.add([["Lead", "creation", "Timespan", value]]);
		});
	}
}

function lead_tile_styles() {
	if (document.getElementById("lead-tile-styles")) return;
	const css = `
.lt-wrap { --lt-blue:#2a78d6; --lt-blue-soft:rgba(42,120,214,.10); --lt-good:#0f7a48; --lt-bad:#c62a2f; --lt-bad-soft:rgba(227,73,72,.10);
	padding: 12px 15px 4px; }
[data-theme="dark"] .lt-wrap { --lt-blue:#3987e5; --lt-blue-soft:rgba(57,135,229,.16); --lt-good:#4cc38a; --lt-bad:#f08585; --lt-bad-soft:rgba(230,103,103,.14); }
.lt-bar { display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; margin-bottom:10px; }
.lt-period { display:flex; gap:4px; flex-wrap:wrap; }
.lt-chip { border:1px solid var(--border-color); background: var(--card-bg); color: var(--text-muted); border-radius: 999px;
	padding: 3px 11px; font-size: var(--text-xs); font-weight:500; cursor:pointer; }
.lt-chip:hover { color: var(--text-color); }
.lt-chip.active { background: var(--text-color); border-color: var(--text-color); color: var(--card-bg); }
.lt-hint { color: var(--text-muted); font-size: var(--text-xs); }
.lt-tiles { display:grid; grid-template-columns: repeat(7, minmax(0,1fr)); gap:10px; }
.lt-tile { text-align:left; background: var(--card-bg); border:1px solid var(--border-color); border-radius: 12px;
	padding: 11px 13px; cursor:pointer; display:flex; flex-direction:column; gap:2px; transition: border-color .12s, box-shadow .12s; min-width:0; }
.lt-tile:hover { border-color: var(--lt-blue); }
.lt-tile:focus-visible { outline: 2px solid var(--lt-blue); outline-offset: 2px; }
.lt-tile.active { border-color: var(--lt-blue); box-shadow: inset 0 3px 0 var(--lt-blue); background: var(--lt-blue-soft); }
.lt-label { font-size: var(--text-xs); color: var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.lt-value { font-size: 22px; font-weight: 650; color: var(--heading-color, var(--text-color)); font-variant-numeric: tabular-nums; letter-spacing:-.01em; }
.lt-foot { font-size: 11px; color: var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.lt-tile.good .lt-value { color: var(--lt-good); }
.lt-tile.bad .lt-value { color: var(--lt-bad); } .lt-tile.bad { background: var(--lt-bad-soft); }
.lt-tile.bad.active { box-shadow: inset 0 3px 0 var(--lt-bad); border-color: var(--lt-bad); }
@media (max-width: 1200px) { .lt-tiles { grid-template-columns: repeat(4, minmax(0,1fr)); } }
@media (max-width: 640px) { .lt-tiles { grid-template-columns: repeat(2, minmax(0,1fr)); } .lt-hint { display:none; } }
`;
	const el = document.createElement("style");
	el.id = "lead-tile-styles";
	el.textContent = css;
	document.head.appendChild(el);
}
