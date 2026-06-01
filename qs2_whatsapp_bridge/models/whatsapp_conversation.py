import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WhatsAppConversation(models.Model):
    _name = "whatsapp.conversation"
    _description = "WhatsApp Conversation"
    _order = "last_message_date desc, id desc"
    _rec_name = "display_name"

    partner_id = fields.Many2one("res.partner", string="Contatto", ondelete="set null")
    phone = fields.Char(string="Telefono", required=True, index=True)
    active = fields.Boolean(
        default=True,
        help="Disattiva per archiviare la conversazione (resta in DB ma non "
             "compare nella sidebar). Stile WhatsApp Web 'archivia chat'.",
    )
    # Chat ID restituito da whatsapp-web.js (es. "393339118902@c.us" o "215830814056597@lid").
    # È lo stesso per messaggi in entrata e in uscita della stessa chat, anche con LID attivo.
    wa_jid = fields.Char(string="WhatsApp Chat ID", index=True)
    # Numero "di servizio" estratto dal wa_jid quando è un LID (Linked Identity di WhatsApp).
    # Visualizzabile a fianco del phone reale per dare visibilità di entrambi gli ID.
    service_id = fields.Char(
        string="ID servizio (LID)",
        compute="_compute_service_id",
        store=True,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)
    last_message_date = fields.Datetime(string="Ultimo messaggio")
    last_message_preview = fields.Char(string="Anteprima")
    unread_count = fields.Integer(string="Non letti", default=0)
    message_ids = fields.One2many(
        "whatsapp.message", "conversation_id", string="Messaggi"
    )
    message_count = fields.Integer(compute="_compute_message_count")

    _sql_constraints = [
        ("phone_unique", "unique(phone)", "Esiste già una conversazione con questo numero."),
    ]

    @api.depends("partner_id", "partner_id.name", "phone")
    def _compute_display_name(self):
        for rec in self:
            if rec.partner_id:
                rec.display_name = rec.partner_id.name
            else:
                rec.display_name = rec.phone or "Sconosciuto"

    @api.depends("wa_jid")
    def _compute_service_id(self):
        for rec in self:
            if rec.wa_jid and "@lid" in rec.wa_jid:
                rec.service_id = rec.wa_jid.split("@", 1)[0]
            else:
                rec.service_id = False

    @api.depends("message_ids")
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    # ------------------------------------------------------------------
    # Archive / unarchive — stile WhatsApp Web
    # ------------------------------------------------------------------
    def action_qs2_archive(self):
        """Archivia: la conversazione resta nel DB ma sparisce dalla lista."""
        self.write({"active": False})
        return True

    def action_qs2_unarchive(self):
        self.write({"active": True})
        return True

    # ------------------------------------------------------------------
    # Send message — API pubblica
    # ------------------------------------------------------------------
    def action_send_message(self, body):
        """Invia un messaggio in questa conversazione."""
        self.ensure_one()
        account = self.env["whatsapp.account"].get_default_account()
        # Invia al chat id stabile (wa_jid) quando disponibile: è esattamente il
        # thread a cui appartengono i messaggi e funziona anche quando il numero
        # del contatto è nascosto dietro un LID. Fallback al numero di telefono.
        to = self.wa_jid if (self.wa_jid and "@" in self.wa_jid) else self.phone
        result = account._bridge_post("/send", {"to": to, "message": body})

        if not result or not result.get("ok"):
            error = result.get("error", "Errore sconosciuto") if result else "Bridge non raggiungibile"
            raise UserError(f"Invio fallito: {error}")

        # Memorizza il chat ID restituito dal bridge: serve a matchare i messaggi
        # in arrivo della stessa chat anche quando il mittente arriva come @lid.
        chat_id = result.get("chatId")
        if chat_id and self.wa_jid != chat_id:
            self.wa_jid = chat_id

        # Crea il messaggio nel DB
        msg = self.env["whatsapp.message"].create({
            "conversation_id": self.id,
            "direction": "out",
            "body": body,
            "wa_message_id": result.get("id", ""),
            "state": "sent",
        })
        self.write({
            "last_message_date": msg.timestamp,
            "last_message_preview": body[:100],
        })
        return msg

    @api.model
    def send_message(self, phone=None, partner_id=None, body=""):
        """
        API pubblica per inviare un messaggio WhatsApp.

        Utilizzabile da qualsiasi modulo Odoo:
            self.env['whatsapp.conversation'].send_message(
                phone='+39328...', body='Ciao!'
            )
            # oppure
            self.env['whatsapp.conversation'].send_message(
                partner_id=partner.id, body='Ciao!'
            )
        """
        if not phone and partner_id:
            partner = self.env["res.partner"].browse(partner_id)
            phone = partner.phone
        if not phone:
            raise UserError("Nessun numero di telefono specificato.")

        # Normalizza il telefono
        phone = phone.strip().replace(" ", "")

        # Trova o crea la conversazione
        conv = self.search([("phone", "=", phone)], limit=1)
        if not conv:
            vals = {"phone": phone}
            if partner_id:
                vals["partner_id"] = partner_id
            conv = self.create(vals)
        elif partner_id and not conv.partner_id:
            conv.partner_id = partner_id

        return conv.action_send_message(body)

    @api.model
    def _maybe_update_phone(self, conv, phone_number):
        """Aggiorna conv.phone solo se il nuovo valore è "migliore" di quello attuale.

        Regole:
        - non sovrascrivere mai se il phone attuale inizia con '+' (è già un numero
          presumibilmente reale, scelto in fase di outbound o da una @c.us);
        - non sovrascrivere mai con la stringa numerica del wa_jid (= la parte
          a sinistra di '@', sia per @c.us che per @lid);
        - aggiornare solo se conv.phone è vuoto.
        """
        if not phone_number:
            return
        new_phone = f"+{phone_number}"
        if conv.phone == new_phone:
            return
        if conv.phone and conv.phone.startswith("+"):
            return  # phone reale già impostato, non lo tocchiamo
        # Bonus check: se phone_number è proprio la parte sinistra del wa_jid LID,
        # è quasi sicuramente spazzatura — non sovrascrivere.
        if conv.wa_jid and phone_number == conv.wa_jid.split("@", 1)[0]:
            return
        conv.phone = new_phone

    # ------------------------------------------------------------------
    # Get or create from incoming message
    # ------------------------------------------------------------------
    @api.model
    def _get_or_create_from_incoming(self, jid, chat_id="", phone_number="", push_name=""):
        """Trova o crea una conversazione da un messaggio in arrivo.

        Args:
            jid: JID del mittente (può essere @c.us o @lid)
            chat_id: ID stabile della chat (chat.id._serialized lato bridge).
                È la chiave preferita perché è la stessa per in/out della stessa chat.
            phone_number: numero reale risolto dal bridge (può essere vuoto se LID)
            push_name: nome visualizzato del contatto
        """
        # 1. Match per chat ID — chiave più stabile, sopravvive ai LID
        if chat_id:
            conv = self.search([("wa_jid", "=", chat_id)], limit=1)
            if conv:
                self._maybe_update_phone(conv, phone_number)
                return conv

        # 2. Fallback per retrocompatibilità: cerca per sender JID
        if jid and jid != chat_id:
            conv = self.search([("wa_jid", "=", jid)], limit=1)
            if conv:
                if chat_id:
                    conv.wa_jid = chat_id  # promuove al chat_id più stabile
                self._maybe_update_phone(conv, phone_number)
                return conv

        # 3. Determina il numero di telefono
        if phone_number:
            phone = f"+{phone_number}"
        elif "@c.us" in (chat_id or jid):
            phone = f"+{(chat_id or jid).split('@')[0]}"
        else:
            # LID senza numero risolto — usiamo il push_name
            phone = push_name or (chat_id or jid).split("@")[0]

        # 4. Cerca per numero di telefono
        if phone.startswith("+"):
            conv = self.search([("phone", "=", phone)], limit=1)
            if conv:
                conv.wa_jid = chat_id or jid
                return conv

        # 5. Cerca un partner con questo numero
        phone_raw = phone.lstrip("+")
        partner = self.env["res.partner"].search(
            [("phone", "ilike", phone_raw)],
            limit=1,
        )

        return self.create({
            "phone": phone,
            "wa_jid": chat_id or jid,
            "partner_id": partner.id if partner else False,
            "display_name": push_name or phone,
        })
