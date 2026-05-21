import json
import logging
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_BRIDGE_URL = "http://localhost:3100"


class WhatsAppAccount(models.Model):
    _name = "whatsapp.account"
    _description = "WhatsApp Account"
    _rec_name = "name"

    name = fields.Char(default="WhatsApp", required=True)
    bridge_url = fields.Char(
        string="Bridge URL",
        default=DEFAULT_BRIDGE_URL,
        required=True,
    )
    state = fields.Selection(
        [
            ("disconnected", "Disconnesso"),
            ("qr", "In attesa QR"),
            ("connected", "Connesso"),
        ],
        string="Stato",
        default="disconnected",
        readonly=True,
    )
    qr_image = fields.Binary(string="QR Code", readonly=True, attachment=False)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
    )

    # ------------------------------------------------------------------
    # Bridge communication helpers
    # ------------------------------------------------------------------
    def _bridge_get(self, path):
        self.ensure_one()
        url = f"{self.bridge_url.rstrip('/')}{path}"
        try:
            req = Request(url)
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except (URLError, ConnectionError, OSError) as exc:
            _logger.warning("Bridge non raggiungibile: %s", exc)
            return None

    def _bridge_post(self, path, data):
        self.ensure_one()
        url = f"{self.bridge_url.rstrip('/')}{path}"
        body = json.dumps(data).encode()
        req = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except (URLError, ConnectionError, OSError) as exc:
            _logger.warning("Bridge errore POST: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_refresh_status(self):
        """Aggiorna stato connessione e QR code dal bridge."""
        self.ensure_one()
        data = self._bridge_get("/status")
        if not data:
            self.write({"state": "disconnected", "qr_image": False})
            return

        status = data.get("status", "disconnected")
        vals = {"state": status}

        if status == "qr":
            qr_data = self._bridge_get("/qr")
            if qr_data and qr_data.get("qr"):
                b64 = qr_data["qr"].split(",", 1)[-1]
                vals["qr_image"] = b64
            else:
                vals["qr_image"] = False
        else:
            vals["qr_image"] = False

        self.write(vals)

    def action_disconnect(self):
        """Disconnetti la sessione WhatsApp."""
        self.ensure_one()
        self.write({"state": "disconnected", "qr_image": False})

    def action_open_conversations(self):
        """Apri la lista conversazioni."""
        return {
            "type": "ir.actions.act_window",
            "name": "Conversazioni",
            "res_model": "whatsapp.conversation",
            "view_mode": "list,form",
        }

    def action_send_test_message(self):
        """Invia un messaggio di test tramite wizard."""
        self.ensure_one()
        if self.state != "connected":
            raise UserError("WhatsApp non connesso. Scansiona il QR code.")
        return {
            "type": "ir.actions.act_window",
            "name": "Invia messaggio di test",
            "res_model": "whatsapp.test.message.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_account_id": self.id},
        }

    @api.model
    def action_open_account(self):
        """Apre la configurazione account, creandolo se non esiste."""
        account = self.get_default_account()
        account.action_refresh_status()
        return {
            "type": "ir.actions.act_window",
            "name": "Configurazione WhatsApp",
            "res_model": "whatsapp.account",
            "view_mode": "form",
            "res_id": account.id,
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Public API — usabile da altri moduli
    # ------------------------------------------------------------------
    @api.model
    def send_message(self, phone, body):
        """
        Invia un messaggio WhatsApp. Utilizzabile da qualsiasi modulo:

            self.env['whatsapp.account'].send_message('+39328...', 'Ciao!')

        Returns dict with message id or raises UserError.
        """
        account = self.search([], limit=1)
        if not account:
            raise UserError("Nessun account WhatsApp configurato.")
        if account.state != "connected":
            raise UserError("WhatsApp non connesso.")

        result = account._bridge_post("/send", {"to": phone, "message": body})
        if not result or not result.get("ok"):
            error = result.get("error", "Errore sconosciuto") if result else "Bridge non raggiungibile"
            raise UserError(f"Invio fallito: {error}")

        return result

    @api.model
    def get_default_account(self):
        """Ritorna l'account di default, creandolo se necessario."""
        account = self.search([], limit=1)
        if not account:
            account = self.create({"name": "WhatsApp"})
        return account

    @api.model
    def _cron_poll_messages(self):
        """Chiamato dal cron per ricevere messaggi dal bridge."""
        account = self.get_default_account()

        # Auto-aggiorna lo stato connessione
        status_data = account._bridge_get("/status")
        if status_data:
            new_state = status_data.get("status", "disconnected")
            if new_state != account.state:
                account.state = new_state
        elif account.state != "disconnected":
            account.state = "disconnected"

        if account.state != "connected":
            return

        data = account._bridge_get("/messages")
        if not data:
            return

        Conversation = self.env["whatsapp.conversation"].sudo()
        Message = self.env["whatsapp.message"].sudo()

        for msg in data:
            jid = msg.get("from", "")
            if not jid or msg.get("isGroup"):
                continue

            wa_id = msg.get("id", "")
            if wa_id and Message.search([("wa_message_id", "=", wa_id)], limit=1):
                continue

            conv = Conversation._get_or_create_from_incoming(
                jid,
                chat_id=msg.get("chatId", ""),
                phone_number=msg.get("phone", ""),
                push_name=msg.get("pushName", ""),
            )

            ts = msg.get("timestamp")
            dt = datetime.fromtimestamp(int(ts)) if ts else datetime.now()

            Message.create({
                "conversation_id": conv.id,
                "direction": "in",
                "body": msg.get("text", ""),
                "wa_message_id": wa_id,
                "timestamp": dt,
                "state": "delivered",
                "author_name": msg.get("pushName", ""),
            })
            conv.write({
                "last_message_date": dt,
                "last_message_preview": msg.get("text", "")[:100],
                "unread_count": conv.unread_count + 1,
            })
