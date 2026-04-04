/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

class KDVDashboard extends Component {
    static template = "kdv_dashboard.KDVDashboard";
    static props = ["*"];

    setup() {
        this.state = useState({
            data: null,
            loading: true,
        });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await rpc("/kdv_dashboard/data", {});
        } catch (e) {
            console.error("KDV Dashboard error:", e);
        }
        this.state.loading = false;
    }

    get monthlyData() {
        if (!this.state.data) return [];
        return this.state.data.monthly || [];
    }

    get quarterly() {
        if (!this.state.data) return null;
        return this.state.data.quarterly;
    }

    get yearly() {
        if (!this.state.data) return null;
        return this.state.data.yearly;
    }

    get periodLabels() {
        if (!this.state.data) return {};
        return this.state.data.period_labels || {};
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat("tr-TR", {
            style: "currency",
            currency: "TRY",
            minimumFractionDigits: 2,
        }).format(amount || 0);
    }

    netCardClass(amount) {
        if (amount >= 0) return "kdv-mini-amount text-danger";
        return "kdv-mini-amount text-primary";
    }

    netCellClass(amount) {
        if (amount > 0) return "text-end text-danger fw-bold";
        if (amount === 0) return "text-end";
        return "text-end text-primary fw-bold";
    }

    rowClass(m) {
        if (m.is_current) return "table-active fw-bold";
        if (m.sales_tax === 0 && m.purchase_tax === 0) return "text-muted";
        return "";
    }

    monthCardClass(m) {
        if (m.is_current) return "kdv-month-card active";
        if (m.sales_tax === 0 && m.purchase_tax === 0) return "kdv-month-card empty";
        return "kdv-month-card";
    }
}

registry.category("actions").add("kdv_dashboard", KDVDashboard);
