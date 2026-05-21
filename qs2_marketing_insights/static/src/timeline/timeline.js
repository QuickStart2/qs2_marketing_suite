/** @odoo-module **/
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Widget OWL incastonato nel form crm.lead come tab "Storia".
 * Chiama crm.lead.get_timeline_events(lead_id) e renderizza una timeline
 * verticale con icone, color coding e click-to-record.
 */
export class LeadTimeline extends Component {
    static template = "qs2_marketing_insights.LeadTimeline";
    static props = {
        record: { type: Object, optional: true },
        readonly: { type: Boolean, optional: true },
        "*": { optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            events: [],
            loading: true,
            expanded: {}, // id -> bool
            filterGroups: {
                marketing: true,
                tracking: true,
                comm: true,
                sales: true,
                billing: true,
                crm: true,
            },
        });

        onWillStart(() => this.loadEvents(this.props.record?.resId));
        onWillUpdateProps((nextProps) => {
            const oldId = this.props.record?.resId;
            const newId = nextProps.record?.resId;
            if (newId && newId !== oldId) {
                this.loadEvents(newId);
            }
        });
    }

    async loadEvents(leadId) {
        if (!leadId) {
            this.state.events = [];
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        try {
            const result = await this.orm.call(
                "crm.lead",
                "get_timeline_events",
                [leadId]
            );
            this.state.events = result || [];
        } catch (err) {
            this.state.events = [];
        }
        this.state.loading = false;
    }

    get filteredEvents() {
        return this.state.events.filter(
            (e) => this.state.filterGroups[e.group] !== false
        );
    }

    toggleGroup(group) {
        this.state.filterGroups[group] = !this.state.filterGroups[group];
    }

    toggleExpand(eventId) {
        this.state.expanded[eventId] = !this.state.expanded[eventId];
    }

    isExpanded(eventId) {
        return !!this.state.expanded[eventId];
    }

    formatDate(iso) {
        if (!iso) return "";
        const d = new Date(iso);
        if (isNaN(d)) return iso;
        return d.toLocaleString("it-IT", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    async openRecord(link) {
        if (!link || !link.res_model || !link.res_id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: link.res_model,
            res_id: link.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

// Registriamo come "view widget" — utilizzabile da XML con
// <widget name="qs2_lead_timeline"/> dentro un <page>.
// NB: in Odoo 19 il framework Widget passa `record` automaticamente nelle props
// (vedi web/static/src/views/widgets/widget.js#widgetProps). NON definire
// extractProps con `({record})` perché destruttura widgetInfo (non ha record)
// e poi sovrascrive il record vero con undefined nello spread finale.
export const leadTimelineWidget = {
    component: LeadTimeline,
};
registry.category("view_widgets").add("qs2_lead_timeline", leadTimelineWidget);
