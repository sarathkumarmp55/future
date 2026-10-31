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
                <span class="lld-card-toggle">
                    <i class="fa fa-chevron-down"></i>
                </span>
            </div>
        `;
    }


    // =====================================================
    // COLLAPSE
    // =====================================================

    get_collapsed_sections() {

        try {
            return JSON.parse(
                localStorage.getItem("lld_collapsed_sections") || "[]"
            );
        } catch (e) {
            return [];
        }
    }


    restore_collapsed_state() {

        const collapsed = this.get_collapsed_sections();

        collapsed.forEach(section => {
            this.$dashboard
                .find(`.lld-card[data-section="${section}"]`)
                .addClass("lld-collapsed")
                .find(".lld-card-body")
                .hide();
        });
    }


    toggle_section($card) {

        const section = $card.data("section");
        const $body = $card.find(".lld-card-body");
        const collapsing = !$card.hasClass("lld-collapsed");

        $card.toggleClass("lld-collapsed", collapsing);

        if (collapsing) {
            $body.slideUp(200);
        } else {
            // charts drawn while hidden have zero width, so redraw on expand
            $body.slideDown(200, () => this.redraw_section(section));
        }

        let collapsed = this.get_collapsed_sections()
            .filter(s => s !== section);

        if (collapsing) {
            collapsed.push(section);
        }

        try {
            localStorage.setItem(
                "lld_collapsed_sections",
                JSON.stringify(collapsed)
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

                height: 280

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

        if ($("#lead-list-dashboard-style-v2").length) {
            return;
        }


        $("head").append(`

            <style id="lead-list-dashboard-style-v2">

                .lead-list-dashboard {
                    --lld-accent: #5b5bd6;
                    --lld-accent-2: #8e4ec6;
                    --lld-radius: 16px;
                    --lld-shadow:
                        0 1px 2px rgba(16, 24, 40, 0.04),
                        0 4px 12px rgba(16, 24, 40, 0.05);
                    --lld-shadow-hover:
                        0 2px 4px rgba(16, 24, 40, 0.05),
                        0 12px 28px rgba(16, 24, 40, 0.10);
                    margin-bottom: 28px;
                }


                .lld-wrapper {
                    width: 100%;
                }


                /* =========================================
                   FILTER
                ========================================= */

                .lld-filter-card {
                    position: relative;
                    overflow: hidden;
                    background:
                        radial-gradient(circle at 85% -20%, rgba(255, 255, 255, 0.28), transparent 45%),
                        radial-gradient(circle at 0% 120%, rgba(255, 255, 255, 0.12), transparent 40%),
                        linear-gradient(120deg, #4f46e5 0%, #6d4fd8 50%, #8e4ec6 100%);
                    border-radius: var(--lld-radius);
                    padding: 22px 26px;
                    margin-bottom: 22px;
                    box-shadow:
                        0 10px 30px -8px rgba(79, 70, 229, 0.45),
                        inset 0 1px 0 rgba(255, 255, 255, 0.18);
                    color: #fff;
                }


                .lld-filter-row {
                    display: flex;
                    align-items: flex-end;
                    gap: 16px;
                    flex-wrap: wrap;
                }


                .lld-filter-field {
                    width: 200px;
                }


                .lld-filter-field label {
                    display: block;
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: rgba(255, 255, 255, 0.85);
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                }


                .lld-filter-field input.form-control {
                    border: 1px solid rgba(255, 255, 255, 0.35);
                    border-radius: 10px;
                    height: 42px;
                    background: rgba(255, 255, 255, 0.96);
                    color: #1f2937;
                    font-weight: 500;
                    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
                    transition: box-shadow 0.2s ease;
                }


                .lld-filter-field input.form-control:focus {
                    box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.45);
                }


                .lld-filter-actions {
                    display: flex;
                    gap: 10px;
                    margin-left: auto;
                }


                .lld-filter-actions .btn {
                    border-radius: 10px;
                    height: 42px;
                    padding: 0 22px;
                    font-weight: 600;
                    border: none;
                    transition: all 0.2s ease;
                }


                .lld-filter-actions .btn-primary {
                    background: #fff;
                    color: #4f46e5;
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
                }


                .lld-filter-actions .btn-primary:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 10px 22px rgba(0, 0, 0, 0.22);
                }


                .lld-filter-actions .btn-default {
                    background: rgba(255, 255, 255, 0.14);
                    color: #fff;
                    border: 1px solid rgba(255, 255, 255, 0.35);
                    backdrop-filter: blur(6px);
                }


                .lld-filter-actions .btn-default:hover {
                    background: rgba(255, 255, 255, 0.24);
                }


                /* =========================================
                   KPI
                ========================================= */

                .lld-kpi-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
                    gap: 16px;
                    margin-bottom: 22px;
                }


                .lld-kpi-card {
                    --kpi: #5b5bd6;
                    --kpi-2: #8e4ec6;
                    position: relative;
                    overflow: hidden;
                    background: var(--card-bg);
                    border: 1px solid var(--border-color);
                    border-radius: var(--lld-radius);
                    padding: 18px 18px 18px 20px;
                    min-height: 104px;
                    display: flex;
                    align-items: center;
                    gap: 14px;
                    box-shadow: var(--lld-shadow);
                    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
                }


                .lld-kpi-card::before {
                    content: "";
                    position: absolute;
                    left: 0;
                    right: 0;
                    top: 0;
                    height: 3px;
                    background: linear-gradient(90deg, var(--kpi), var(--kpi-2));
                    opacity: 0.9;
                }


                .lld-kpi-card::after {
                    content: "";
                    position: absolute;
                    right: -40px;
                    bottom: -40px;
                    width: 120px;
                    height: 120px;
                    border-radius: 50%;
                    background: radial-gradient(circle, color-mix(in srgb, var(--kpi) 14%, transparent), transparent 70%);
                    pointer-events: none;
                }


                .lld-kpi-card:hover {
                    transform: translateY(-2px);
                    box-shadow: var(--lld-shadow-hover);
                    border-color: color-mix(in srgb, var(--kpi) 35%, var(--border-color));
                }


                .lld-kpi-icon {
                    width: 46px;
                    height: 46px;
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 19px;
                    flex-shrink: 0;
                    color: #fff;
                    background: linear-gradient(135deg, var(--kpi), var(--kpi-2));
                    box-shadow: 0 6px 14px -4px color-mix(in srgb, var(--kpi) 60%, transparent);
                }


                .lld-kpi-total      { --kpi: #4f46e5; --kpi-2: #7c6ff0; }
                .lld-kpi-new        { --kpi: #d946ef; --kpi-2: #f472b6; }
                .lld-kpi-contacted  { --kpi: #0ea5e9; --kpi-2: #38bdf8; }
                .lld-kpi-interested { --kpi: #f59e0b; --kpi-2: #fbbf24; }
                .lld-kpi-counselled { --kpi: #10b981; --kpi-2: #34d399; }
                .lld-kpi-admissions { --kpi: #e11d48; --kpi-2: #fb7185; }
                .lld-kpi-conversion { --kpi: #7c3aed; --kpi-2: #a78bfa; }
                .lld-kpi-assigned   { --kpi: #f97316; --kpi-2: #fb923c; }


                .lld-kpi-content {
                    position: relative;
                    z-index: 1;
                    min-width: 0;
                }


                .lld-kpi-title {
                    font-size: 11px;
                    color: var(--text-muted);
                    margin-bottom: 4px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.07em;
                    line-height: 1.35;
                }


                .lld-kpi-value {
                    font-size: 28px;
                    font-weight: 700;
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
                    gap: 20px;
                    margin-bottom: 20px;
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
                    transition: box-shadow 0.2s ease;
                }


                .lld-card:hover {
                    box-shadow: var(--lld-shadow-hover);
                }


                .lld-card-header {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 16px 20px;
                    cursor: pointer;
                    user-select: none;
                    border-bottom: 1px solid var(--border-color);
                    transition: background 0.15s ease;
                }


                .lld-card-header:hover {
                    background: var(--subtle-fg, rgba(0, 0, 0, 0.02));
                }


                .lld-card-header:focus-visible {
                    outline: 2px solid var(--lld-accent);
                    outline-offset: -2px;
                }


                .lld-card-icon {
                    width: 32px;
                    height: 32px;
                    border-radius: 9px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 14px;
                    color: var(--lld-accent);
                    background: color-mix(in srgb, var(--lld-accent) 12%, transparent);
                    flex-shrink: 0;
                }


                .lld-card-title {
                    flex: 1;
                    font-size: 15px;
                    font-weight: 600;
                    color: var(--text-color);
                    letter-spacing: -0.01em;
                }


                .lld-card-toggle {
                    width: 28px;
                    height: 28px;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: var(--text-muted);
                    font-size: 11px;
                    transition: transform 0.25s ease, background 0.15s ease, color 0.15s ease;
                }


                .lld-card-header:hover .lld-card-toggle {
                    background: color-mix(in srgb, var(--lld-accent) 10%, transparent);
                    color: var(--lld-accent);
                }


                .lld-card.lld-collapsed .lld-card-toggle {
                    transform: rotate(-90deg);
                }


                .lld-card.lld-collapsed .lld-card-header {
                    border-bottom-color: transparent;
                }


                .lld-card-body {
                    padding: 20px;
                }


                /* =========================================
                   EMPTY STATE
                ========================================= */

                .lld-empty {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 6px;
                    padding: 36px 16px;
                    text-align: center;
                }


                .lld-empty-icon {
                    width: 52px;
                    height: 52px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    margin-bottom: 6px;
                    color: var(--lld-accent);
                    background: color-mix(in srgb, var(--lld-accent) 10%, transparent);
                }


                .lld-empty-text {
                    font-size: 14px;
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
                    gap: 20px;
                    min-height: 200px;
                    flex-wrap: wrap;
                }


                .lld-gender-item {
                    text-align: center;
                    min-width: 120px;
                    padding: 20px 18px;
                    border-radius: 14px;
                    background: var(--card-bg);
                    border: 1px solid var(--border-color);
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                }


                .lld-gender-item:hover {
                    transform: translateY(-3px);
                    box-shadow: var(--lld-shadow-hover);
                }


                .lld-gender-avatar {
                    width: 56px;
                    height: 56px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 22px;
                    margin: 0 auto 12px;
                    color: #fff;
                }


                .lld-gender-male .lld-gender-avatar {
                    background: linear-gradient(135deg, #0ea5e9, #6366f1);
                    box-shadow: 0 6px 14px -4px rgba(14, 165, 233, 0.6);
                }


                .lld-gender-female .lld-gender-avatar {
                    background: linear-gradient(135deg, #f43f5e, #d946ef);
                    box-shadow: 0 6px 14px -4px rgba(244, 63, 94, 0.6);
                }


                .lld-gender-unknown .lld-gender-avatar {
                    background: linear-gradient(135deg, #8b5cf6, #a78bfa);
                    box-shadow: 0 6px 14px -4px rgba(139, 92, 246, 0.6);
                }


                .lld-gender-count {
                    font-size: 34px;
                    font-weight: 700;
                    color: var(--text-color);
                    letter-spacing: -0.02em;
                    font-variant-numeric: tabular-nums;
                }


                .lld-gender-label {
                    font-size: 12px;
                    color: var(--text-muted);
                    margin-top: 4px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.07em;
                }


                /* =========================================
                   SOURCE
                ========================================= */

                .lld-source-chart {
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }


                /* =========================================
                   STATUS
                ========================================= */

                .lld-status-card {
                    width: 100%;
                    margin-bottom: 20px;
                }


                .lld-status-card .lld-card-body {
                    overflow-x: auto;
                }


                .lld-status-chart {
                    width: 100%;
                }


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

                    .lld-filter-card {
                        padding: 18px;
                    }

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
                        gap: 12px;
                    }

                    .lld-kpi-card {
                        padding: 14px;
                        gap: 10px;
                    }

                    .lld-kpi-icon {
                        width: 38px;
                        height: 38px;
                        font-size: 15px;
                    }

                    .lld-kpi-value {
                        font-size: 22px;
                    }

                    .lld-gender-stats {
                        gap: 12px;
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
