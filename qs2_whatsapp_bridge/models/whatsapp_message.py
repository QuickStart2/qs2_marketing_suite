from odoo import api, fields, models


class WhatsAppMessage(models.Model):
    _name = "whatsapp.message"
    _description = "WhatsApp Message"
    _order = "timestamp asc"

    conversation_id = fields.Many2one(
        "whatsapp.conversation",
        string="Conversazione",
        required=True,
        ondelete="cascade",
        index=True,
    )
    direction = fields.Selection(
        [("in", "Ricevuto"), ("out", "Inviato")],
        string="Direzione",
        required=True,
    )
    body = fields.Text(string="Messaggio")
    timestamp = fields.Datetime(
        string="Data/ora",
        default=fields.Datetime.now,
        index=True,
    )
    wa_message_id = fields.Char(string="WhatsApp ID", index=True)
    state = fields.Selection(
        [
            ("pending", "In attesa"),
            ("sent", "Inviato"),
            ("delivered", "Consegnato"),
            ("read", "Letto"),
            ("failed", "Fallito"),
        ],
        string="Stato",
        default="sent",
    )
    author_name = fields.Char(string="Autore")
    partner_id = fields.Many2one(
        related="conversation_id.partner_id",
        string="Contatto",
        store=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Posta ogni messaggio anche nel chatter dei lead/opportunity aperti
        # collegati al contatto WhatsApp, così il venditore lo vede in scheda.
        for msg in records:
            try:
                msg._post_to_related_leads()
            except Exception:  # noqa: BLE001
                # Non bloccare la creazione del messaggio per un problema di logging
                pass
        return records

    def _post_to_related_leads(self):
        """Pubblica questo messaggio WhatsApp nel chatter dei lead aperti del partner."""
        self.ensure_one()
        Lead = self.env["crm.lead"].sudo()

        # 1. Match per partner_id (se la conversazione è stata collegata a un res.partner)
        leads = Lead.browse()
        if self.partner_id:
            leads = Lead.search([
                ("partner_id", "=", self.partner_id.id),
                ("active", "=", True),
            ], limit=5)

        # 2. Fallback: match per phone del conversation
        if not leads and self.conversation_id.phone:
            leads = Lead.search([
                ("phone", "=", self.conversation_id.phone),
                ("active", "=", True),
            ], limit=5)

        if not leads:
            return

        # Costruisci il body del chatter
        prefix = "📩 WhatsApp" if self.direction == "in" else "📤 WhatsApp"
        author = self.author_name or self.conversation_id.display_name or ""
        body = (
            f"<p><strong>{prefix}</strong>"
            + (f" — <em>{author}</em>" if author else "")
            + f"</p><blockquote>{(self.body or '').replace(chr(10), '<br/>')}</blockquote>"
        )
        for lead in leads:
            lead.message_post(
                body=body,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
