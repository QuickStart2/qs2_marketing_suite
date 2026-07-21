import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

export class LeadsKanban extends Interaction {
    static selector = ".o_leads_kanban";
    dynamicContent = {
        ".o_leads_card": {
            "t-on-dragstart": this.onDragStart,
            "t-on-dragend": this.onDragEnd,
        },
        ".o_leads_col_body": {
            "t-on-dragover.prevent": () => {},   // abilita il drop
            "t-on-drop.prevent": this.onDrop,
        },
    };

    setup() {
        this.notification = this.services.notification;
        this.draggedCard = null;
    }

    onDragStart(ev) {
        this.draggedCard = ev.currentTarget;
        ev.dataTransfer.setData("text/plain", this.draggedCard.dataset.leadId);
        ev.dataTransfer.effectAllowed = "move";
        this.draggedCard.classList.add("o_dragging");
    }

    onDragEnd() {
        this.draggedCard?.classList.remove("o_dragging");
    }

    async onDrop(ev) {
        const body = ev.currentTarget;                 // .o_leads_col_body target
        const card = this.draggedCard;
        if (!card || card.parentElement === body) {
            return;
        }
        const leadId = parseInt(card.dataset.leadId);
        const stageId = parseInt(body.dataset.stageId);
        const previousBody = card.parentElement;
        // spostamento ottimistico (sposto lo stesso nodo → i listener restano)
        body.appendChild(card);
        this.updateCounts(previousBody);
        this.updateCounts(body);
        let message = null;
        try {
            const res = await this.waitFor(
                rpc(`/my/leads/${leadId}/set_stage`, { stage_id: stageId })
            );
            if (!res || !res.ok) {
                message = (res && res.message) || _t("Impossibile spostare il lead.");
            }
        } catch {
            message = _t("Impossibile spostare il lead.");
        }
        if (message) {
            previousBody.appendChild(card);            // rollback
            this.updateCounts(previousBody);
            this.updateCounts(body);
            this.notification.add(message, { type: "warning" });
        }
    }

    updateCounts(colBody) {
        const col = colBody.closest(".o_leads_col");
        const badge = col?.querySelector(".o_leads_col_count");
        if (badge) {
            badge.textContent = colBody.querySelectorAll(".o_leads_card").length;
        }
    }
}

registry.category("public.interactions").add("qs2_crm_portal.leads_kanban", LeadsKanban);
