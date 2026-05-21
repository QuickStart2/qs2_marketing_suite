/** @odoo-module **/
/**
 * Patcha il componente Chatter di mail per aggiungere un bottone "WhatsApp"
 * accanto a "Send message" / "Log note". Visibile solo per crm.lead.
 *
 * Cliccando si apre il wizard qs2.whatsapp.lead.wizard, già esistente.
 */
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Chatter } from "@mail/chatter/web_portal/chatter";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.qs2Action = useService("action");
    },
    qs2IsWhatsAppEnabled() {
        return this.props.threadModel === "crm.lead" && this.props.threadId;
    },
    async openQs2WhatsAppWizard() {
        if (!this.qs2IsWhatsAppEnabled()) return;
        this.qs2Action.doAction({
            type: "ir.actions.act_window",
            name: "Invia WhatsApp",
            res_model: "qs2.whatsapp.lead.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_lead_id: this.props.threadId,
            },
        });
    },
});
