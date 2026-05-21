/** @odoo-module */
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class WhatsAppChat extends Component {
    static template = "qs2_whatsapp_bridge.WhatsAppChat";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.messagesEndRef = useRef("messagesEnd");
        this.messageInputRef = useRef("messageInput");

        this.state = useState({
            conversations: [],
            activeConversationId: null,
            messages: [],
            inputText: "",
            loading: false,
            bridgeStatus: "unknown",
            qrImage: null,
            showNewChat: false,
            newChatPhone: "",
            searchQuery: "",
            showArchived: false,
        });

        // Se arriva un conversation_id dal params, lo usiamo
        const params = this.props.action?.params || {};
        if (params.conversation_id) {
            this.state.activeConversationId = params.conversation_id;
        }

        onWillStart(async () => {
            await this.loadConversations();
            await this.checkStatus();
        });

        onMounted(() => {
            this._pollInterval = setInterval(() => this.pollMessages(), 5000);
            if (this.state.activeConversationId) {
                this.loadMessages(this.state.activeConversationId);
            }
        });
    }

    willUnmount() {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
        }
    }

    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------
    async checkStatus() {
        try {
            const result = await rpc("/whatsapp/status", {});
            this.state.bridgeStatus = result.status;
        } catch {
            this.state.bridgeStatus = "error";
        }
    }

    async loadConversations() {
        try {
            const result = await rpc("/whatsapp/conversations", {
                include_archived: this.state.showArchived,
            });
            // Ordina per last_message_date desc (stile WhatsApp Web)
            result.sort((a, b) => {
                const da = a.last_message_date ? new Date(a.last_message_date).getTime() : 0;
                const db = b.last_message_date ? new Date(b.last_message_date).getTime() : 0;
                return db - da;
            });
            this.state.conversations = result;
        } catch {
            this.state.conversations = [];
        }
    }

    toggleShowArchived() {
        this.state.showArchived = !this.state.showArchived;
        this.loadConversations();
    }

    async toggleArchive(ev, conv) {
        // Non aprire la conversazione cliccando sul bottone
        ev.stopPropagation();
        ev.preventDefault();
        const archive = conv.active !== false; // se attiva → archivia
        try {
            await rpc("/whatsapp/archive", {
                conversation_id: conv.id,
                archive,
            });
            await this.loadConversations();
            // Se ho archiviato la conv selezionata, deselezionala
            if (archive && this.state.activeConversationId === conv.id) {
                this.state.activeConversationId = null;
                this.state.messages = [];
            }
        } catch {
            this.notification.add("Impossibile archiviare la conversazione", { type: "danger" });
        }
    }

    async loadMessages(conversationId) {
        this.state.loading = true;
        this.state.activeConversationId = conversationId;
        try {
            this.state.messages = await rpc("/whatsapp/messages", {
                conversation_id: conversationId,
            });
            // Aggiorna unread nella lista
            const conv = this.state.conversations.find((c) => c.id === conversationId);
            if (conv) conv.unread_count = 0;
        } catch {
            this.state.messages = [];
        }
        this.state.loading = false;
        this.scrollToBottom();
    }

    async pollMessages() {
        try {
            const incoming = await rpc("/whatsapp/poll_bridge", {});
            if (incoming && incoming.length) {
                await this.loadConversations();
                if (this.state.activeConversationId) {
                    const hasNew = incoming.some(
                        (m) => m.conversation_id === this.state.activeConversationId
                    );
                    if (hasNew) {
                        await this.loadMessages(this.state.activeConversationId);
                    }
                }
            }
        } catch {
            // silently ignore poll errors
        }
    }

    // ------------------------------------------------------------------
    // Actions
    // ------------------------------------------------------------------
    async selectConversation(conv) {
        await this.loadMessages(conv.id);
        this.focusInput();
    }

    async sendMessage() {
        const body = this.state.inputText.trim();
        if (!body || !this.state.activeConversationId) return;

        this.state.inputText = "";
        try {
            const result = await rpc("/whatsapp/send", {
                conversation_id: this.state.activeConversationId,
                body,
            });
            if (result.ok) {
                this.state.messages.push(result.message);
                this.scrollToBottom();
                // Aggiorna anteprima nella lista
                const conv = this.state.conversations.find(
                    (c) => c.id === this.state.activeConversationId
                );
                if (conv) {
                    conv.last_message_preview = body.substring(0, 100);
                    conv.last_message_date = new Date().toISOString();
                }
            } else {
                this.notification.add(result.error || "Errore invio", { type: "danger" });
            }
        } catch {
            this.notification.add("Errore di connessione", { type: "danger" });
        }
    }

    onKeyDown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    onInputChange(ev) {
        this.state.inputText = ev.target.value;
    }

    async createNewConversation() {
        const phone = this.state.newChatPhone.trim();
        if (!phone) return;
        try {
            const result = await rpc("/whatsapp/new_conversation", { phone });
            this.state.showNewChat = false;
            this.state.newChatPhone = "";
            await this.loadConversations();
            await this.loadMessages(result.id);
        } catch {
            this.notification.add("Errore creazione conversazione", { type: "danger" });
        }
    }

    toggleNewChat() {
        this.state.showNewChat = !this.state.showNewChat;
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------
    scrollToBottom() {
        setTimeout(() => {
            const el = this.messagesEndRef.el;
            if (el) el.scrollIntoView({ behavior: "smooth" });
        }, 100);
    }

    focusInput() {
        setTimeout(() => {
            const el = this.messageInputRef.el;
            if (el) el.focus();
        }, 100);
    }

    formatTime(isoStr) {
        if (!isoStr) return "";
        const d = new Date(isoStr);
        return d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
    }

    formatDate(isoStr) {
        if (!isoStr) return "";
        const d = new Date(isoStr);
        const today = new Date();
        if (d.toDateString() === today.toDateString()) return "Oggi";
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        if (d.toDateString() === yesterday.toDateString()) return "Ieri";
        return d.toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });
    }

    getActiveConversation() {
        return this.state.conversations.find(
            (c) => c.id === this.state.activeConversationId
        );
    }

    getFilteredConversations() {
        const q = this.state.searchQuery.toLowerCase();
        if (!q) return this.state.conversations;
        return this.state.conversations.filter(
            (c) =>
                (c.display_name || "").toLowerCase().includes(q) ||
                (c.phone || "").includes(q)
        );
    }

    getInitials(name) {
        if (!name) return "?";
        return name
            .split(" ")
            .map((w) => w[0])
            .join("")
            .substring(0, 2)
            .toUpperCase();
    }

    getStateIcon(state) {
        switch (state) {
            case "sent": return "fa-check";
            case "delivered": return "fa-check-double";
            case "read": return "fa-check-double text-primary";
            case "failed": return "fa-times text-danger";
            default: return "fa-clock-o";
        }
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    onNewChatPhoneInput(ev) {
        this.state.newChatPhone = ev.target.value;
    }
}

registry.category("actions").add("qs2_whatsapp_bridge.chat", WhatsAppChat);
