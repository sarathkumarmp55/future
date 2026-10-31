frappe.listview_settings["Lead"] = {

    refresh(listview) {

        if (!listview.page.main.find(".lead-list-dashboard").length) {

            listview.page.main.prepend(`
                <div class="lead-list-dashboard"></div>
            `);

            new LeadListDashboard(listview);
        }
    }
};


// Muted slate palette that sits with the neutral Frappe desk theme.
const LLD_CHART_COLORS = [
    "#334155",
    "#64748b",
    "#94a3b8",
    "#475569",
    "#cbd5e1",
    "#1e293b",
    "#7c8798",
    "#e2e8f0",
];


class LeadListDashboard {

    constructor(listview) {

        this.listview = listview;

        this.$dashboard = listview.page.main.find(
            ".lead-list-dashboard"
        );

        this.from_date = frappe.datetime.get_today();
        this.to_date = frappe.datetime.get_today();

        this.render();
        this.load_dashboard_data();
    }


    // =====================================================
    // RENDER
    // =====================================================

    render() {

        this.$dashboard.html(`

            <div class="lld-wrapper">

                <!-- ======================================
                     DATE FILTER
                ======================================= -->

                <div class="lld-filter-card">

                    <div class="lld-filter-row">

                        <div class="lld-filter-field">

                            <label>
                                From Date
                            </label>

                            <input
                                type="date"
                                class="form-control lld-from-date"
                                value="${this.from_date}"
                            >

                        </div>


                        <div class="lld-filter-field">

                            <label>
                                To Date
                            </label>

                            <input
                                type="date"
                                class="form-control lld-to-date"
                                value="${this.to_date}"
                            >

                        </div>


                        <div class="lld-filter-actions">

                            <button
                                class="btn btn-primary lld-apply-btn"
                            >
                                Apply
                            </button>

                            <button
                                class="btn btn-default lld-today-btn"
                            >
                                Today
                            </button>

                        </div>

                    </div>

                </div>


                <!-- ======================================
                     KPI CARDS
                ======================================= -->

                <div class="lld-kpi-grid">

                    <div class="lld-kpi-card lld-kpi-total">

                        <div class="lld-kpi-icon">
                            <i class="fa fa-users"></i>
                        </div>

                        <div class="lld-kpi-content">

                            <div class="lld-kpi-title">
                                Total Leads
                            </div>

                            <div
                                class="lld-kpi-value"
                                data-kpi="total"
                            >
                                0
                            </div>

                        </div>

                    </div>


                    <div class="lld-kpi-card lld-kpi-new">

                        <div class="lld-kpi-icon">
                            <i class="fa fa-user-plus"></i>
                        </div>

                        <div class="lld-kpi-content">

                            <div class="lld-kpi-title">
                                New Leads
                            </div>

                            <div
                                class="lld-kpi-value"
                                data-kpi="new_leads"
                            >
                                0
                            </div>

                        </div>

                    </div>


                    <div class="lld-kpi-card lld-kpi-contacted">

                        <div class="lld-kpi-icon">
                            <i class="fa fa-phone"></i>
                        </div>

                        <div class="lld-kpi-content">

                            <div class="lld-kpi-title">
                                Contacted
                            </div>

                            <div
                                class="lld-kpi-value"
                                data-kpi="contacted"
                            >
                                0
                            </div>

                        </div>

                    </div>


                    <div class="lld-kpi-card lld-kpi-interested">

                        <div class="lld-kpi-icon">
                            <i class="fa fa-star"></i>
                        </div>

                        <div class="lld-kpi-content">

                            <div class="lld-kpi-title">
                                Interested
                            </div>

                            <div
                                class="lld-kpi-value"
                                data-kpi="interested"
                            >
                                0
                            </div>

                        </div>

                    </div>


                    <div class="lld-kpi-card lld-kpi-counselled">

                        <div class="lld-kpi-icon">
                            <i class="fa fa-comments"></i>
                        </div>

                        <div class="lld-kpi-content">

                            <div class="lld-kpi-title">
                                Counselled
                            </div>

                            <div
                                class="lld-kpi-value"
                                data-kpi="counselled"
                            >
                                0
                            </div>

                        </div>

                    </div>


                    <div class="lld-kpi-card lld-kpi-admissions">

                        <div class="lld-kpi-icon">
                            <i class="fa fa-graduation-cap"></i>
                        </div>

                        <div class="lld-kpi-content">

                            <div class="lld-kpi-title">
                                Admissions
                            </div>

                            <div
                                class="lld-kpi-value"
                                data-kpi="admissions"
                            >
                                0
                            </div>

                        </div>

                    </div>


                    <div class="lld-kpi-card lld-kpi-conversion">

                        <div class="lld-kpi-icon">
                            <i class="fa fa-percent"></i>
                        </div>

                        <div class="lld-kpi-content">

                            <div class="lld-kpi-title">
                                Conversion Rate
                            </div>

                            <div
                                class="lld-kpi-value"
                                data-kpi="conversion_rate"
                            >
                                0%
                            </div>

                        </div>

                    </div>


                    <div class="lld-kpi-card lld-kpi-assigned">

                        <div class="lld-kpi-icon">
                            <i class="fa fa-handshake-o"></i>
                        </div>

                        <div class="lld-kpi-content">

                            <div class="lld-kpi-title">
                                Assigned Leads
                            </div>

                            <div
                                class="lld-kpi-value"
                                data-kpi="assigned_leads"
                            >
                                0
                            </div>

                        </div>

                    </div>

                </div>


                <!-- ======================================
                     GENDER + SOURCE
                ======================================= -->

                <div class="lld-two-column">

                    <!-- Gender -->

                    <div class="lld-card" data-section="gender">

                        ${this.card_header("Gender Distribution", "venus-mars")}

                        <div class="lld-card-body">
                            <div class="lld-gender-stats">
                                <div class="text-muted text-center">
                                    Loading...
                                </div>
                            </div>
                        </div>

                    </div>


                    <!-- Source -->

                    <div class="lld-card" data-section="source">

                        ${this.card_header("Lead Source", "pie-chart")}

                        <div class="lld-card-body">
                            <div
                                class="lld-source-chart"
                            ></div>
                        </div>

                    </div>

                </div>


                <!-- ======================================
                     STATUS
                ======================================= -->

                <div class="lld-card lld-status-card" data-section="status">

                    ${this.card_header("Leads by Status", "bar-chart")}

                    <div class="lld-card-body">
                        <div
                            class="lld-status-chart"
                        ></div>
                    </div>

                </div>

            </div>

        `);


        this.bind_events();
        this.add_styles();
        this.restore_collapsed_state();
    }


    empty_state(icon, text) {

        return `
            <div class="lld-empty">
                <div class="lld-empty-icon">
                    <i class="fa fa-${icon}"></i>
                </div>
                <div class="lld-empty-text">${text}</div>
                <div class="lld-empty-hint">Try a wider date range</div>
            </div>
        `;
    }


    card_header(title, icon) {

        return `
            <div class="lld-card-header" role="button" tabindex="0">
                <span class="lld-card-icon">
                    <i class="fa fa-${icon}"></i>
                </span>
                <span class="lld-card-title">${title}</span>
                <span class="lld-card-pin" role="button" tabindex="0" title="${__("Pin open")}">
                    <i class="fa fa-thumb-tack"></i>
                </span>
                <span class="lld-card-toggle">
                    <i class="fa fa-chevron-down"></i>
                </span>
            </div>
        `;
    }


    // =====================================================
    // COLLAPSE / PIN
    // =====================================================

    // Cards start collapsed; only pinned cards open on load.
    get_pinned_sections() {

        try {
            return JSON.parse(
                localStorage.getItem("lld_pinned_sections") || "[]"
            );
        } catch (e) {
            return [];
        }
    }


    restore_collapsed_state() {

        const pinned = this.get_pinned_sections();

        this.$dashboard.find(".lld-card[data-section]").each((i, card) => {

            const $card = $(card);
            const is_pinned = pinned.includes($card.data("section"));

            $card.toggleClass("lld-pinned", is_pinned);
            $card.toggleClass("lld-collapsed", !is_pinned);
            $card.find(".lld-card-body").toggle(is_pinned);
        });
    }


    set_expanded($card, expand) {

        const $body = $card.find(".lld-card-body");

        if (expand === !$card.hasClass("lld-collapsed")) {
            return;
        }

        $card.toggleClass("lld-collapsed", !expand);

        if (expand) {
            // charts drawn while hidden have zero width, so redraw on expand
            $body.slideDown(200, () => this.redraw_section($card.data("section")));
        } else {
            $body.slideUp(200);
        }
    }


    toggle_section($card) {

        this.set_expanded($card, $card.hasClass("lld-collapsed"));
    }


    toggle_pin($card) {

        const section = $card.data("section");
        const pinning = !$card.hasClass("lld-pinned");

        $card.toggleClass("lld-pinned", pinning);

        if (pinning) {
            this.set_expanded($card, true);
        }

        let pinned = this.get_pinned_sections()
            .filter(s => s !== section);

        if (pinning) {
            pinned.push(section);
        }

        try {
            localStorage.setItem(
                "lld_pinned_sections",
                JSON.stringify(pinned)
            );
        } catch (e) {
            // ignore storage failures
        }
    }


    redraw_section(section) {

        if (!this.data) {
            return;
        }

        if (section === "source") {
            this.render_source_chart();
        } else if (section === "status") {
            this.render_status_chart();
        }
    }


    // =====================================================
    // EVENTS
    // =====================================================

    bind_events() {

        this.$dashboard
            .find(".lld-card-pin")
            .on("click", (e) => {
                e.stopPropagation();
                this.toggle_pin($(e.currentTarget).closest(".lld-card"));
            })
            .on("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    e.stopPropagation();
                    this.toggle_pin($(e.currentTarget).closest(".lld-card"));
                }
            });

        this.$dashboard
            .find(".lld-card-header")
            .on("click", (e) => {
                this.toggle_section($(e.currentTarget).closest(".lld-card"));
            })
            .on("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    this.toggle_section($(e.currentTarget).closest(".lld-card"));
                }
            });


        this.$dashboard
            .find(".lld-apply-btn")
            .on("click", () => {

                this.from_date = this.$dashboard
                    .find(".lld-from-date")
                    .val();

                this.to_date = this.$dashboard
                    .find(".lld-to-date")
                    .val();

                this.load_dashboard_data();
            });


        this.$dashboard
            .find(".lld-today-btn")
            .on("click", () => {

                const today = frappe.datetime.get_today();

                this.from_date = today;
                this.to_date = today;

                this.$dashboard
                    .find(".lld-from-date")
                    .val(today);

                this.$dashboard
                    .find(".lld-to-date")
                    .val(today);

                this.load_dashboard_data();
            });

    }


    // =====================================================
    // LOAD DATA
    // =====================================================

    load_dashboard_data() {

        frappe.call({

            method: "future.api.get_dashboard_data",

            args: {

                filters: {

                    from_date: this.from_date,

                    to_date: this.to_date

                }

            },

            freeze: false,

            callback: (r) => {

                if (!r.message) {
                    return;
                }

                this.data = r.message;

                this.render_kpis();

                this.render_gender_distribution();

                this.render_source_chart();

                this.render_status_chart();

            }

        });

    }


    // =====================================================
    // KPI
    // =====================================================

    render_kpis() {

        const kpis = this.data.kpis || {};

        this.set_kpi(
            "total",
            kpis.total || 0
        );

        this.set_kpi(
            "new_leads",
            kpis.new_leads || 0
        );

        this.set_kpi(
            "contacted",
            kpis.contacted || 0
        );

        this.set_kpi(
            "interested",
            kpis.interested || 0
        );

        this.set_kpi(
            "counselled",
            kpis.counselled || 0
        );

        this.set_kpi(
            "admissions",
            kpis.admissions || 0
        );

        this.set_kpi(
            "conversion_rate",
            `${kpis.conversion_rate || 0}%`
        );

        this.set_kpi(
            "assigned_leads",
            kpis.assigned_leads || 0
        );

    }


    set_kpi(name, value) {

        this.$dashboard
            .find(`[data-kpi="${name}"]`)
            .text(value);

    }


    // =====================================================
    // GENDER
    // =====================================================

    render_gender_distribution() {

        const genders = this.data.gender || [];

        const container = this.$dashboard.find(
            ".lld-gender-stats"
        );


        if (!genders.length) {

            container.html(this.empty_state("venus-mars", "No gender data available"));

            return;
        }


        let html = "";

        const gender_meta = {
            "Male": { icon: "male", color: "male" },
            "Female": { icon: "female", color: "female" },
            "Unknown": { icon: "user", color: "unknown" }
        };

        genders.forEach(item => {

            const gender = item.gender || "Unknown";
            const meta = gender_meta[gender] || gender_meta["Unknown"];

            html += `

                <div class="lld-gender-item lld-gender-${meta.color}">

                    <div class="lld-gender-avatar">
                        <i class="fa fa-${meta.icon}"></i>
                    </div>

                    <div class="lld-gender-count">
                        ${item.total_count || 0}
                    </div>

                    <div class="lld-gender-label">
                        ${frappe.utils.escape_html(gender)}
                    </div>

                </div>

            `;

        });


        container.html(html);

    }


    // =====================================================
    // SOURCE CHART
    // =====================================================

    render_source_chart() {

        const sources = this.data.sources || [];

        const container = this.$dashboard.find(
            ".lld-source-chart"
        );


        if (!sources.length) {

            container.html(this.empty_state("pie-chart", "No source data available"));

            return;
        }


        const chartData = {

            labels: sources.map(
                item => item.source || "Unknown"
            ),

            datasets: [
                {
                    name: "Leads",

                    values: sources.map(
                        item => item.total_count || 0
                    )
                }
            ]

        };


        container.empty();


        this.source_chart = new frappe.Chart(
            container[0],
            {

                data: chartData,

                type: "donut",

                height: 280,

                colors: LLD_CHART_COLORS

            }
        );

    }


    // =====================================================
    // STATUS CHART
    // =====================================================

    render_status_chart() {

        const statuses = this.data.statuses || [];

        const container = this.$dashboard.find(
            ".lld-status-chart"
        );


        if (!statuses.length) {

            container.html(this.empty_state("bar-chart", "No status data available"));

            return;
        }


        const chartData = {

            labels: statuses.map(
                item => item.status || "Unknown"
            ),

            datasets: [
                {

                    name: "Leads",

                    values: statuses.map(
                        item => item.total_count || 0
                    )

                }
            ]

        };


        container.empty();


        this.status_chart = new frappe.Chart(
            container[0],
            {

                data: chartData,

                type: "bar",

                height: 420,

                colors: [LLD_CHART_COLORS[0]],

                barOptions: {

                    spaceRatio: 0.25

                },

                axisOptions: {

                    xAxisMode: "tick",

                    yAxisMode: "tick",

                    xIsSeries: true

                },

                tooltipOptions: {

                    formatTooltipY: value => {
                        return `${value} Leads`;
                    }

                }

            }
        );

    }


    // =====================================================
    // CSS
    // =====================================================

    add_styles() {

        if ($("#lead-list-dashboard-style-v3").length) {
            return;
        }


        $("head").append(`

            <style id="lead-list-dashboard-style-v3">

                .lead-list-dashboard {
                    --lld-radius: 12px;
                    --lld-ink: var(--gray-900, #171717);
                    --lld-tile: var(--subtle-fg, #f3f3f3);
                    --lld-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
                    --lld-shadow-hover: 0 4px 14px rgba(0, 0, 0, 0.06);
                    margin-bottom: 24px;
                }


                .lld-wrapper {
                    width: 100%;
                }


                /* =========================================
                   FILTER
                ========================================= */

                .lld-filter-card {
                    background: var(--card-bg);
                    border: 1px solid var(--border-color);
                    border-radius: var(--lld-radius);
                    padding: 16px 20px;
                    margin-bottom: 16px;
                    box-shadow: var(--lld-shadow);
                }


                .lld-filter-row {
                    display: flex;
                    align-items: flex-end;
                    gap: 14px;
                    flex-wrap: wrap;
                }


                .lld-filter-field {
                    width: 190px;
                }


                .lld-filter-field label {
                    display: block;
                    margin-bottom: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                }


                .lld-filter-field input.form-control {
                    height: 36px;
                    border-radius: 8px;
                }


                .lld-filter-actions {
                    display: flex;
                    gap: 8px;
                    margin-left: auto;
                }


                .lld-filter-actions .btn {
                    height: 36px;
                    padding: 0 16px;
                    border-radius: 8px;
                    font-weight: 500;
                }


                /* =========================================
                   KPI
                ========================================= */

                .lld-kpi-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
                    gap: 12px;
                    margin-bottom: 16px;
                }


                .lld-kpi-card {
                    background: var(--card-bg);
                    border: 1px solid var(--border-color);
                    border-radius: var(--lld-radius);
                    padding: 16px 18px;
                    min-height: 92px;
                    display: flex;
                    align-items: center;
                    gap: 14px;
                    box-shadow: var(--lld-shadow);
                    transition: box-shadow 0.2s ease, border-color 0.2s ease;
                }


                .lld-kpi-card:hover {
                    box-shadow: var(--lld-shadow-hover);
                    border-color: var(--gray-300, #d4d4d4);
                }


                .lld-kpi-icon {
                    width: 40px;
                    height: 40px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 16px;
                    flex-shrink: 0;
                    color: var(--text-color);
                    background: var(--lld-tile);
                }


                /* the headline metrics get the solid ink tile */
                .lld-kpi-total .lld-kpi-icon,
                .lld-kpi-admissions .lld-kpi-icon {
                    color: var(--card-bg);
                    background: var(--lld-ink);
                }


                .lld-kpi-content {
                    min-width: 0;
                }


                .lld-kpi-title {
                    font-size: 11px;
                    font-weight: 600;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                    line-height: 1.35;
                    margin-bottom: 4px;
                }


                .lld-kpi-value {
                    font-size: 24px;
                    font-weight: 600;
                    color: var(--text-color);
                    line-height: 1.1;
                    letter-spacing: -0.02em;
                    font-variant-numeric: tabular-nums;
                }


                /* =========================================
                   CARDS
                ========================================= */

                .lld-two-column {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                    margin-bottom: 12px;
                    align-items: start;
                }


                .lld-card {
                    background: var(--card-bg);
                    border: 1px solid var(--border-color);
                    border-radius: var(--lld-radius);
                    box-shadow: var(--lld-shadow);
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }


                .lld-card-header {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 12px 16px;
                    cursor: pointer;
                    user-select: none;
                    border-bottom: 1px solid var(--border-color);
                    transition: background 0.15s ease;
                }


                .lld-card-header:hover {
                    background: var(--subtle-accent, #f8f8f8);
                }


                .lld-card-header:focus-visible,
                .lld-card-pin:focus-visible {
                    outline: 2px solid var(--lld-ink);
                    outline-offset: -2px;
                }


                .lld-card-icon {
                    width: 30px;
                    height: 30px;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 13px;
                    color: var(--text-color);
                    background: var(--lld-tile);
                    flex-shrink: 0;
                }


                .lld-card-title {
                    flex: 1;
                    font-size: 14px;
                    font-weight: 600;
                    color: var(--text-color);
                }


                .lld-card-pin,
                .lld-card-toggle {
                    width: 28px;
                    height: 28px;
                    border-radius: 6px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: var(--text-muted);
                    font-size: 12px;
                    transition: transform 0.2s ease, background 0.15s ease, color 0.15s ease, opacity 0.15s ease;
                }


                .lld-card-pin {
                    opacity: 0;
                    transform: rotate(45deg);
                }


                .lld-card-header:hover .lld-card-pin,
                .lld-card-pin:focus-visible,
                .lld-card.lld-pinned .lld-card-pin {
                    opacity: 1;
                }


                .lld-card-pin:hover,
                .lld-card-toggle:hover {
                    background: var(--lld-tile);
                    color: var(--text-color);
                }


                .lld-card.lld-pinned .lld-card-pin {
                    color: var(--card-bg);
                    background: var(--lld-ink);
                    transform: rotate(0deg);
                }


                .lld-card.lld-collapsed .lld-card-toggle {
                    transform: rotate(-90deg);
                }


                .lld-card.lld-collapsed .lld-card-header {
                    border-bottom-color: transparent;
                }


                .lld-card-body {
                    padding: 16px;
                }


                /* =========================================
                   EMPTY STATE
                ========================================= */

                .lld-empty {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                    padding: 32px 16px;
                    text-align: center;
                }


                .lld-empty-icon {
                    width: 44px;
                    height: 44px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 17px;
                    margin-bottom: 6px;
                    color: var(--text-muted);
                    background: var(--lld-tile);
                }


                .lld-empty-text {
                    font-size: 13px;
                    font-weight: 600;
                    color: var(--text-color);
                }


                .lld-empty-hint {
                    font-size: 12px;
                    color: var(--text-muted);
                }


                /* =========================================
                   GENDER
                ========================================= */

                .lld-gender-stats {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 12px;
                    min-height: 180px;
                    flex-wrap: wrap;
                }


                .lld-gender-item {
                    text-align: center;
                    min-width: 120px;
                    padding: 18px 16px;
                    border-radius: 10px;
                    background: var(--card-bg);
                    border: 1px solid var(--border-color);
                }


                .lld-gender-avatar {
                    width: 44px;
                    height: 44px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                    margin: 0 auto 10px;
                    color: var(--text-color);
                    background: var(--lld-tile);
                }


                .lld-gender-count {
                    font-size: 28px;
                    font-weight: 600;
                    color: var(--text-color);
                    letter-spacing: -0.02em;
                    font-variant-numeric: tabular-nums;
                }


                .lld-gender-label {
                    font-size: 11px;
                    color: var(--text-muted);
                    margin-top: 2px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                }


                /* =========================================
                   SOURCE / STATUS
                ========================================= */

                .lld-source-chart {
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }


                .lld-status-card {
                    width: 100%;
                    margin-bottom: 16px;
                }


                .lld-status-card .lld-card-body {
                    overflow-x: auto;
                }


                .lld-status-chart,
                .lld-status-chart .frappe-chart {
                    width: 100%;
                }


                /* =========================================
                   RESPONSIVE
                ========================================= */

                @media (max-width: 900px) {

                    .lld-two-column {
                        grid-template-columns: 1fr;
                    }

                }


                @media (max-width: 600px) {

                    .lld-filter-field {
                        width: 100%;
                    }

                    .lld-filter-actions {
                        width: 100%;
                        margin-left: 0;
                    }

                    .lld-filter-actions button {
                        flex: 1;
                    }

                    .lld-kpi-grid {
                        grid-template-columns: repeat(2, 1fr);
                        gap: 10px;
                    }

                    .lld-kpi-card {
                        padding: 12px;
                        gap: 10px;
                    }

                    .lld-kpi-icon {
                        width: 34px;
                        height: 34px;
                        font-size: 14px;
                    }

                    .lld-kpi-value {
                        font-size: 20px;
                    }

                    .lld-card-pin {
                        opacity: 1;
                    }

                }

            </style>

        `);

    }

}

function patch_assign_to_dialog_role_field() {
    const AssignToDialog = frappe.ui.form && frappe.ui.form.AssignToDialog;
    if (!AssignToDialog || AssignToDialog.prototype.__future_role_field) return;
    AssignToDialog.prototype.__future_role_field = true;

    const _get_fields = AssignToDialog.prototype.get_fields;
    AssignToDialog.prototype.get_fields = function () {
        const fields = _get_fields.call(this);
        const idx = fields.findIndex((f) => f.fieldname === "assign_to");
        if (idx === -1) {
            return fields;
        }
        fields.splice(idx + 1, 0, {
            label: __("Role"),
            fieldtype: "Select",
            fieldname: "custom_role",
            options: "\nTeam Lead\nLead Manager\nLead User",
            reqd: 1,
        });
        return fields;
    };

    const _make = AssignToDialog.prototype.make;
    AssignToDialog.prototype.make = function () {
        _make.call(this);

        const me = this;
        const dialog = this.dialog;
        const _primary_action = dialog.primary_action;

        dialog.set_primary_action(dialog.primary_action_label || __("Add"), function () {
            const role = dialog.get_value("custom_role");
            const assign_to = dialog.get_value("assign_to");
            const _call = frappe.call;

            frappe.call = function (opts) {
                if (opts && opts.method === "frappe.desk.form.assign_to.add_multiple" && opts.args) {
                    const _callback = opts.callback;
                    opts.callback = function (r) {
                        if (r && !r.exc && role && assign_to && assign_to.length) {
                            frappe.xcall("future.api.set_lead_assignment_role", {
                                doctype: me.doctype,
                                names: me.docname,
                                allocated_to: assign_to[0],
                                role: role,
                            });
                        }
                        return _callback && _callback.apply(this, arguments);
                    };
                }
                return _call.apply(this, arguments);
            };

            try {
                return _primary_action.apply(this, arguments);
            } finally {
                frappe.call = _call;
            }
        });
    };
}

patch_assign_to_dialog_role_field();
