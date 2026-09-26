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

                    <div class="lld-card">

                        <div class="lld-card-header">
                            Gender Distribution
                        </div>

                        <div class="lld-gender-stats">
                            <div class="text-muted text-center">
                                Loading...
                            </div>
                        </div>

                    </div>


                    <!-- Source -->

                    <div class="lld-card">

                        <div class="lld-card-header">
                            Lead Source
                        </div>

                        <div
                            class="lld-source-chart"
                        ></div>

                    </div>

                </div>


                <!-- ======================================
                     STATUS
                ======================================= -->

                <div class="lld-card lld-status-card">

                    <div class="lld-card-header">
                        Leads by Status
                    </div>

                    <div
                        class="lld-status-chart"
                    ></div>

                </div>

            </div>

        `);


        this.bind_events();
        this.add_styles();
    }


    // =====================================================
    // EVENTS
    // =====================================================

    bind_events() {

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

            container.html(`
                <div class="text-muted text-center">
                    No gender data available
                </div>
            `);

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

            container.html(`
                <div class="text-muted text-center">
                    No source data available
                </div>
            `);

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

            container.html(`
                <div class="text-muted text-center">
                    No status data available
                </div>
            `);

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

        if ($("#lead-list-dashboard-style").length) {
            return;
        }


        $("head").append(`

            <style id="lead-list-dashboard-style">

                .lead-list-dashboard {
                    margin-bottom: 25px;
                }


                .lld-wrapper {
                    width: 100%;
                }


                /* =========================================
                   FILTER
                ========================================= */

                .lld-filter-card {

                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 14px;

                    padding: 20px 24px;

                    margin-bottom: 20px;

                    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.25);
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

                    color: rgba(255, 255, 255, 0.9);
                    font-size: 13px;
                    text-transform: uppercase;
                    letter-spacing: 0.4px;

                }


                .lld-filter-field input.form-control {

                    border: none;
                    border-radius: 10px;
                    height: 42px;
                    background: rgba(255, 255, 255, 0.95);
                    color: #333;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

                }


                .lld-filter-actions {

                    display: flex;

                    gap: 10px;

                    margin-left: auto;

                }


                .lld-filter-actions .btn {

                    border-radius: 10px;
                    padding: 9px 20px;
                    font-weight: 600;
                    border: none;
                    transition: all 0.2s ease;

                }


                .lld-filter-actions .btn-primary {

                    background: #fff;
                    color: #667eea;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);

                }


                .lld-filter-actions .btn-primary:hover {

                    transform: translateY(-2px);
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);

                }


                .lld-filter-actions .btn-default {

                    background: rgba(255, 255, 255, 0.2);
                    color: #fff;

                }


                .lld-filter-actions .btn-default:hover {

                    background: rgba(255, 255, 255, 0.3);

                }


                /* =========================================
                   KPI
                ========================================= */

                .lld-kpi-grid {

                    display: grid;

                    grid-template-columns:
                        repeat(
                            auto-fit,
                            minmax(180px, 1fr)
                        );

                    gap: 16px;

                    margin-bottom: 20px;

                }


                .lld-kpi-card {

                    background: var(--card-bg);

                    border-radius: 14px;

                    padding: 20px;

                    min-height: 110px;

                    display: flex;
                    align-items: center;
                    gap: 16px;

                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);

                    border: 1px solid
                        var(--border-color);

                    transition:
                        transform 0.2s ease,
                        box-shadow 0.2s ease;

                    position: relative;
                    overflow: hidden;

                }


                .lld-kpi-card::before {

                    content: "";
                    position: absolute;
                    left: 0;
                    top: 0;
                    bottom: 0;
                    width: 5px;

                }


                .lld-kpi-card:hover {

                    transform: translateY(-3px);
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);

                }


                .lld-kpi-icon {

                    width: 52px;
                    height: 52px;
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 22px;
                    flex-shrink: 0;
                    background: rgba(0, 0, 0, 0.04);

                }


                .lld-kpi-total::before { background: #667eea; }
                .lld-kpi-total .lld-kpi-icon {
                    color: #667eea;
                    background: rgba(102, 126, 234, 0.12);
                }


                .lld-kpi-new::before { background: #f093fb; }
                .lld-kpi-new .lld-kpi-icon {
                    color: #f093fb;
                    background: rgba(240, 147, 251, 0.12);
                }


                .lld-kpi-contacted::before { background: #4facfe; }
                .lld-kpi-contacted .lld-kpi-icon {
                    color: #4facfe;
                    background: rgba(79, 172, 254, 0.12);
                }


                .lld-kpi-interested::before { background: #f6d365; }
                .lld-kpi-interested .lld-kpi-icon {
                    color: #f6a827;
                    background: rgba(246, 211, 101, 0.18);
                }


                .lld-kpi-counselled::before { background: #43e97b; }
                .lld-kpi-counselled .lld-kpi-icon {
                    color: #2ecc71;
                    background: rgba(67, 233, 123, 0.12);
                }


                .lld-kpi-admissions::before { background: #fa709a; }
                .lld-kpi-admissions .lld-kpi-icon {
                    color: #fa709a;
                    background: rgba(250, 112, 154, 0.12);
                }


                .lld-kpi-conversion::before { background: #a18cd1; }
                .lld-kpi-conversion .lld-kpi-icon {
                    color: #a18cd1;
                    background: rgba(161, 140, 209, 0.12);
                }


                .lld-kpi-assigned::before { background: #ff9a9e; }
                .lld-kpi-assigned .lld-kpi-icon {
                    color: #ff9a9e;
                    background: rgba(255, 154, 158, 0.12);
                }


                .lld-kpi-title {

                    font-size: 12px;

                    color: var(--text-muted);

                    margin-bottom: 6px;

                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;

                }


                .lld-kpi-value {

                    font-size: 28px;

                    font-weight: 700;

                    color: var(--text-color);

                    line-height: 1.1;

                }


                /* =========================================
                   TWO COLUMN
                ========================================= */

                .lld-two-column {

                    display: grid;

                    grid-template-columns:
                        1fr 1fr;

                    gap: 20px;

                    margin-bottom: 20px;

                    align-items: stretch;

                }


                .lld-card {

                    background: var(--card-bg);

                    border: 1px solid
                        var(--border-color);

                    border-radius: 14px;

                    padding: 22px;

                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);

                    display: flex;
                    flex-direction: column;

                }


                .lld-card-header {

                    font-size: 16px;

                    font-weight: 700;

                    margin-bottom: 18px;

                    color: var(--text-color);

                    display: flex;
                    align-items: center;
                    gap: 10px;

                }


                .lld-card-header::before {

                    content: "";
                    width: 4px;
                    height: 20px;
                    border-radius: 2px;
                    background: linear-gradient(180deg, #667eea, #764ba2);

                }


                /* =========================================
                   GENDER
                ========================================= */

                .lld-gender-stats {

                    display: flex;

                    align-items: center;

                    justify-content: center;

                    gap: 40px;

                    min-height: 230px;

                    flex-wrap: wrap;

                }


                .lld-gender-item {

                    text-align: center;

                    min-width: 110px;

                    padding: 18px;

                    border-radius: 16px;

                    background: var(--card-bg);

                    border: 1px solid
                        var(--border-color);

                    transition: transform 0.2s ease;

                }


                .lld-gender-item:hover {

                    transform: translateY(-4px);

                }


                .lld-gender-avatar {

                    width: 64px;
                    height: 64px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 26px;
                    margin: 0 auto 12px;
                    background: rgba(0, 0, 0, 0.04);

                }


                .lld-gender-male .lld-gender-avatar {
                    color: #4facfe;
                    background: rgba(79, 172, 254, 0.15);
                }


                .lld-gender-female .lld-gender-avatar {
                    color: #fa709a;
                    background: rgba(250, 112, 154, 0.15);
                }


                .lld-gender-unknown .lld-gender-avatar {
                    color: #a18cd1;
                    background: rgba(161, 140, 209, 0.15);
                }


                .lld-gender-count {

                    font-size: 38px;

                    font-weight: 700;

                    color: var(--text-color);

                }


                .lld-gender-label {

                    font-size: 14px;

                    color: var(--text-muted);

                    margin-top: 6px;

                    font-weight: 600;

                }


                /* =========================================
                   SOURCE
                ========================================= */

                .lld-source-chart {

                    width: 100%;

                    min-height: 280px;

                    display: flex;
                    align-items: center;
                    justify-content: center;

                }


                /* =========================================
                   STATUS
                ========================================= */

                .lld-status-card {

                    width: 100%;

                    overflow-x: auto;

                    margin-bottom: 20px;

                }


                .lld-status-chart {

                    width: 100%;

                    min-height: 420px;

                    padding: 10px 5px 20px;

                }


                .lld-status-chart .frappe-chart {

                    width: 100%;

                }


                /* =========================================
                   RESPONSIVE
                ========================================= */

                @media (max-width: 1100px) {

                    .lld-kpi-grid {

                        grid-template-columns:
                            repeat(
                                auto-fit,
                                minmax(160px, 1fr)
                            );

                    }

                }


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


                    .lld-gender-stats {

                        gap: 16px;

                    }


                    .lld-kpi-card {

                        padding: 16px;

                    }


                    .lld-kpi-icon {

                        width: 44px;
                        height: 44px;
                        font-size: 18px;

                    }


                    .lld-kpi-value {

                        font-size: 24px;

                    }

                }

            </style>

        `);

    }

}