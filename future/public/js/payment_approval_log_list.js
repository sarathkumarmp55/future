frappe.listview_settings["Payment Approval Log"] = {

    refresh(listview) {

        if (!listview.page.main.find(".pal-list-dashboard").length) {

            listview.page.main.prepend(`
                <div class="pal-list-dashboard"></div>
            `);

            new PaymentApprovalLogListDashboard(listview);
        }
    }
};


class PaymentApprovalLogListDashboard {

    constructor(listview) {

        this.listview = listview;

        this.$dashboard = listview.page.main.find(
            ".pal-list-dashboard"
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

            <div class="pld-wrapper">

                <!-- ======================================
                     DATE FILTER
                ======================================= -->

                <div class="pld-filter-card">

                    <div class="pld-filter-row">

                        <div class="pld-filter-field">

                            <label>
                                From Date
                            </label>

                            <input
                                type="date"
                                class="form-control pld-from-date"
                                value="${this.from_date}"
                            >

                        </div>


                        <div class="pld-filter-field">

                            <label>
                                To Date
                            </label>

                            <input
                                type="date"
                                class="form-control pld-to-date"
                                value="${this.to_date}"
                            >

                        </div>


                        <div class="pld-filter-actions">

                            <button
                                class="btn btn-primary pld-apply-btn"
                            >
                                Apply
                            </button>

                            <button
                                class="btn btn-default pld-today-btn"
                            >
                                Today
                            </button>

                        </div>

                    </div>

                </div>


                <!-- ======================================
                     AMOUNT SUMMARY
                ======================================= -->

                <div class="pld-amount-grid">

                    <div class="pld-amount-card pld-amount-total">

                        <div class="pld-amount-icon">
                            <i class="fa fa-inr"></i>
                        </div>

                        <div class="pld-amount-info">

                            <div class="pld-amount-label">
                                Total Bill Amount
                            </div>

                            <div
                                class="pld-amount-value"
                                data-kpi="total_bill_amount"
                            >
                                0
                            </div>

                        </div>

                    </div>


                    <div class="pld-amount-card pld-amount-fees">

                        <div class="pld-amount-icon">
                            <i class="fa fa-book"></i>
                        </div>

                        <div class="pld-amount-info">

                            <div class="pld-amount-label">
                                Fees Received
                            </div>

                            <div
                                class="pld-amount-value"
                                data-kpi="fees_amount"
                            >
                                0
                            </div>

                        </div>

                    </div>


                    <div class="pld-amount-card pld-amount-hostel">

                        <div class="pld-amount-icon">
                            <i class="fa fa-bed"></i>
                        </div>

                        <div class="pld-amount-info">

                            <div class="pld-amount-label">
                                Hostel Received
                            </div>

                            <div
                                class="pld-amount-value"
                                data-kpi="hostel_amount"
                            >
                                0
                            </div>

                        </div>

                    </div>


                    <div class="pld-amount-card pld-amount-vehicle">

                        <div class="pld-amount-icon">
                            <i class="fa fa-bus"></i>
                        </div>

                        <div class="pld-amount-info">

                            <div class="pld-amount-label">
                                Vehicle Received
                            </div>

                            <div
                                class="pld-amount-value"
                                data-kpi="vehicle_amount"
                            >
                                0
                            </div>

                        </div>

                    </div>

                </div>


                <!-- ======================================
                     STATUS COUNTERS
                ======================================= -->

                <div class="pld-status-grid">

                    <div class="pld-status-card pld-status-total">

                        <div class="pld-status-icon">
                            <i class="fa fa-list"></i>
                        </div>

                        <div class="pld-status-count" data-kpi="total">
                            0
                        </div>

                        <div class="pld-status-label">
                            Total Logs
                        </div>

                    </div>


                    <div class="pld-status-card pld-status-pending">

                        <div class="pld-status-icon">
                            <i class="fa fa-hourglass-half"></i>
                        </div>

                        <div class="pld-status-count" data-kpi="pending">
                            0
                        </div>

                        <div class="pld-status-label">
                            Pending
                        </div>

                    </div>


                    <div class="pld-status-card pld-status-approved">

                        <div class="pld-status-icon">
                            <i class="fa fa-check-circle"></i>
                        </div>

                        <div class="pld-status-count" data-kpi="approved">
                            0
                        </div>

                        <div class="pld-status-label">
                            Approved
                        </div>

                    </div>


                    <div class="pld-status-card pld-status-rejected">

                        <div class="pld-status-icon">
                            <i class="fa fa-times-circle"></i>
                        </div>

                        <div class="pld-status-count" data-kpi="rejected">
                            0
                        </div>

                        <div class="pld-status-label">
                            Rejected
                        </div>

                    </div>


                    <div class="pld-status-card pld-status-opportunity">

                        <div class="pld-status-icon">
                            <i class="fa fa-briefcase"></i>
                        </div>

                        <div class="pld-status-count" data-kpi="from_opportunity">
                            0
                        </div>

                        <div class="pld-status-label">
                            From Opportunity
                        </div>

                    </div>


                    <div class="pld-status-card pld-status-service">

                        <div class="pld-status-icon">
                            <i class="fa fa-user-graduate"></i>
                        </div>

                        <div class="pld-status-count" data-kpi="from_student_service">
                            0
                        </div>

                        <div class="pld-status-label">
                            From Student Service
                        </div>

                    </div>

                </div>


                <!-- ======================================
                     CHARTS
                ======================================= -->

                <div class="pld-charts-row">

                    <div class="pld-chart-card">

                        <div class="pld-chart-header">
                            Request Source
                        </div>

                        <div class="pld-source-chart"></div>

                    </div>


                    <div class="pld-chart-card pld-chart-wide">

                        <div class="pld-chart-header">
                            Payment Status
                        </div>

                        <div class="pld-status-chart"></div>

                    </div>

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
            .find(".pld-apply-btn")
            .on("click", () => {

                this.from_date = this.$dashboard
                    .find(".pld-from-date")
                    .val();

                this.to_date = this.$dashboard
                    .find(".pld-to-date")
                    .val();

                this.load_dashboard_data();
            });


        this.$dashboard
            .find(".pld-today-btn")
            .on("click", () => {

                const today = frappe.datetime.get_today();

                this.from_date = today;
                this.to_date = today;

                this.$dashboard
                    .find(".pld-from-date")
                    .val(today);

                this.$dashboard
                    .find(".pld-to-date")
                    .val(today);

                this.load_dashboard_data();
            });

    }


    // =====================================================
    // LOAD DATA
    // =====================================================

    load_dashboard_data() {

        frappe.call({

            method: "future.api.get_payment_approval_dashboard_data",

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
            "pending",
            kpis.pending || 0
        );

        this.set_kpi(
            "approved",
            kpis.approved || 0
        );

        this.set_kpi(
            "rejected",
            kpis.rejected || 0
        );

        this.set_kpi(
            "from_opportunity",
            kpis.from_opportunity || 0
        );

        this.set_kpi(
            "from_student_service",
            kpis.from_student_service || 0
        );

        this.set_kpi(
            "total_bill_amount",
            frappe.format(
                kpis.total_bill_amount || 0,
                { fieldtype: "Currency" }
            )
        );

        this.set_kpi(
            "fees_amount",
            frappe.format(
                kpis.fees_amount || 0,
                { fieldtype: "Currency" }
            )
        );

        this.set_kpi(
            "hostel_amount",
            frappe.format(
                kpis.hostel_amount || 0,
                { fieldtype: "Currency" }
            )
        );

        this.set_kpi(
            "vehicle_amount",
            frappe.format(
                kpis.vehicle_amount || 0,
                { fieldtype: "Currency" }
            )
        );

    }


    set_kpi(name, value) {

        this.$dashboard
            .find(`[data-kpi="${name}"]`)
            .html(value);

    }


    // =====================================================
    // SOURCE CHART
    // =====================================================

    render_source_chart() {

        const sources = this.data.sources || [];

        const container = this.$dashboard.find(
            ".pld-source-chart"
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
                    name: "Logs",

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

                height: 300,

                colors: ["#667eea", "#f093fb"]

            }
        );

    }


    // =====================================================
    // STATUS CHART
    // =====================================================

    render_status_chart() {

        const statuses = this.data.statuses || [];

        const container = this.$dashboard.find(
            ".pld-status-chart"
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

                    name: "Logs",

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

                height: 300,

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
                        return `${value} Logs`;
                    }

                },

                colors: ["#667eea"]

            }
        );

    }


    // =====================================================
    // CSS
    // =====================================================

    add_styles() {

        if ($("#pal-list-dashboard-style").length) {
            return;
        }


        $("head").append(`

            <style id="pal-list-dashboard-style">

                .pal-list-dashboard {
                    margin-bottom: 25px;
                }


                .pld-wrapper {
                    width: 100%;
                }


                /* =========================================
                   FILTER
                ========================================= */

                .pld-filter-card {

                    background: linear-gradient(135deg, #0ba360 0%, #3cba92 100%);
                    border-radius: 16px;

                    padding: 22px 26px;

                    margin-bottom: 22px;

                    box-shadow: 0 10px 28px rgba(11, 163, 96, 0.22);
                    color: #fff;

                }


                .pld-filter-row {

                    display: flex;

                    align-items: flex-end;

                    gap: 16px;

                    flex-wrap: wrap;

                }


                .pld-filter-field {

                    width: 200px;

                }


                .pld-filter-field label {

                    display: block;

                    font-weight: 600;

                    margin-bottom: 8px;

                    color: rgba(255, 255, 255, 0.9);
                    font-size: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;

                }


                .pld-filter-field input.form-control {

                    border: none;
                    border-radius: 10px;
                    height: 44px;
                    background: rgba(255, 255, 255, 0.96);
                    color: #333;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    font-weight: 500;

                }


                .pld-filter-actions {

                    display: flex;

                    gap: 10px;

                    margin-left: auto;

                }


                .pld-filter-actions .btn {

                    border-radius: 10px;
                    padding: 10px 22px;
                    font-weight: 600;
                    border: none;
                    transition: all 0.2s ease;

                }


                .pld-filter-actions .btn-primary {

                    background: #fff;
                    color: #0ba360;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);

                }


                .pld-filter-actions .btn-primary:hover {

                    transform: translateY(-2px);
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);

                }


                .pld-filter-actions .btn-default {

                    background: rgba(255, 255, 255, 0.2);
                    color: #fff;

                }


                .pld-filter-actions .btn-default:hover {

                    background: rgba(255, 255, 255, 0.32);

                }


                /* =========================================
                   AMOUNT SUMMARY
                ========================================= */

                .pld-amount-grid {

                    display: grid;

                    grid-template-columns: repeat(4, 1fr);

                    gap: 18px;

                    margin-bottom: 18px;

                }


                .pld-amount-card {

                    border-radius: 16px;

                    padding: 24px;

                    color: #fff;

                    display: flex;
                    align-items: center;
                    gap: 16px;

                    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);

                    transition:
                        transform 0.2s ease,
                        box-shadow 0.2s ease;

                }


                .pld-amount-card:hover {

                    transform: translateY(-4px);
                    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.18);

                }


                .pld-amount-total {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }


                .pld-amount-fees {
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }


                .pld-amount-hostel {
                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                }


                .pld-amount-vehicle {
                    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                }


                .pld-amount-icon {

                    width: 56px;
                    height: 56px;
                    border-radius: 14px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 26px;
                    flex-shrink: 0;
                    background: rgba(255, 255, 255, 0.2);
                    backdrop-filter: blur(4px);

                }


                .pld-amount-info {

                    flex: 1;
                    min-width: 0;

                }


                .pld-amount-label {

                    font-size: 13px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.6px;
                    margin-bottom: 6px;
                    opacity: 0.92;

                }


                .pld-amount-value {

                    font-size: 24px;
                    font-weight: 700;
                    line-height: 1.2;
                    word-break: break-word;

                }


                /* =========================================
                   STATUS COUNTERS
                ========================================= */

                .pld-status-grid {

                    display: grid;

                    grid-template-columns: repeat(6, 1fr);

                    gap: 14px;

                    margin-bottom: 22px;

                }


                .pld-status-card {

                    background: var(--card-bg);

                    border-radius: 14px;

                    padding: 18px 14px;

                    text-align: center;

                    border: 1px solid var(--border-color);

                    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);

                    transition:
                        transform 0.2s ease,
                        box-shadow 0.2s ease;

                    position: relative;
                    overflow: hidden;

                }


                .pld-status-card::before {

                    content: "";
                    position: absolute;
                    left: 0;
                    top: 0;
                    right: 0;
                    height: 4px;

                }


                .pld-status-card:hover {

                    transform: translateY(-3px);
                    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.1);

                }


                .pld-status-total::before { background: #667eea; }
                .pld-status-pending::before { background: #f6a827; }
                .pld-status-approved::before { background: #2ecc71; }
                .pld-status-rejected::before { background: #fa709a; }
                .pld-status-opportunity::before { background: #4facfe; }
                .pld-status-service::before { background: #f093fb; }


                .pld-status-icon {

                    width: 44px;
                    height: 44px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    margin: 0 auto 10px;
                    background: rgba(0, 0, 0, 0.04);
                    color: var(--text-muted);

                }


                .pld-status-total .pld-status-icon { color: #667eea; background: rgba(102, 126, 234, 0.1); }
                .pld-status-pending .pld-status-icon { color: #f6a827; background: rgba(246, 168, 39, 0.12); }
                .pld-status-approved .pld-status-icon { color: #2ecc71; background: rgba(46, 204, 113, 0.1); }
                .pld-status-rejected .pld-status-icon { color: #fa709a; background: rgba(250, 112, 154, 0.1); }
                .pld-status-opportunity .pld-status-icon { color: #4facfe; background: rgba(79, 172, 254, 0.1); }
                .pld-status-service .pld-status-icon { color: #c244ce; background: rgba(240, 147, 251, 0.12); }


                .pld-status-count {

                    font-size: 26px;
                    font-weight: 700;
                    color: var(--text-color);
                    line-height: 1;
                    margin-bottom: 6px;

                }


                .pld-status-label {

                    font-size: 12px;
                    font-weight: 600;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.4px;

                }


                /* =========================================
                   CHARTS
                ========================================= */

                .pld-charts-row {

                    display: grid;

                    grid-template-columns: 360px 1fr;

                    gap: 20px;

                }


                .pld-chart-card {

                    background: var(--card-bg);

                    border: 1px solid var(--border-color);

                    border-radius: 16px;

                    padding: 22px;

                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);

                }


                .pld-chart-wide {

                    min-width: 0;

                }


                .pld-chart-header {

                    font-size: 15px;
                    font-weight: 700;
                    color: var(--text-color);
                    margin-bottom: 18px;
                    display: flex;
                    align-items: center;
                    gap: 10px;

                }


                .pld-chart-header::before {

                    content: "";
                    width: 4px;
                    height: 18px;
                    border-radius: 2px;
                    background: linear-gradient(180deg, #0ba360, #3cba92);

                }


                .pld-source-chart,
                .pld-status-chart {

                    width: 100%;
                    min-height: 300px;
                    display: flex;
                    align-items: center;
                    justify-content: center;

                }


                /* =========================================
                   RESPONSIVE
                ========================================= */

                @media (max-width: 1200px) {

                    .pld-amount-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }


                    .pld-status-grid {
                        grid-template-columns: repeat(3, 1fr);
                    }


                    .pld-charts-row {
                        grid-template-columns: 1fr;
                    }

                }


                @media (max-width: 700px) {

                    .pld-amount-grid {
                        grid-template-columns: 1fr;
                    }


                    .pld-status-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }


                    .pld-filter-field {
                        width: 100%;
                    }


                    .pld-filter-actions {
                        width: 100%;
                        margin-left: 0;
                    }


                    .pld-filter-actions button {
                        flex: 1;
                    }

                }

            </style>

        `);

    }

}
