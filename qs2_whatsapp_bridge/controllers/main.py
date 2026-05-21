import json
import logging
from datetime import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WhatsAppController(http.Controller):

    def _get_account(self):
        return request.env["whatsapp.account"].sudo().get_default_account()

    # ------------------------------------------------------------------
    # API endpoints per il frontend OWL
    # ------------------------------------------------------------------
    @http.route("/whatsapp/status", type="json", auth="user")
    def get_status(self):
        account = self._get_account()
        account.action_refresh_status()
        return {"status": account.state}

    @http.route("/whatsapp/qr", type="json", auth="user")
    def get_qr(self):
        account = self._get_account()
        account.action_refresh_status()
        qr_b64 = account.qr_image.decode() if account.qr_image else None
        return {
            "status": account.state,
            "qr": qr_b64,
        }

    @http.route("/whatsapp/send", type="json", auth="user")
    def send_message(self, conversation_id, body):
        conv = request.env["whatsapp.conversation"].browse(int(conversation_id))
        if not conv.exists():
            return {"error": "Conversazione non trovata"}
        msg = conv.action_send_message(body)
        return {
            "ok": True,
            "message": {
                "id": msg.id,
                "body": msg.body,
                "direction": msg.direction,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                "state": msg.state,
            },
        }

    @http.route("/whatsapp/conversations", type="json", auth="user")
    def get_conversations(self, include_archived=False):
        Conv = request.env["whatsapp.conversation"]
        if include_archived:
            Conv = Conv.with_context(active_test=False)
        convs = Conv.search([], limit=100)
        return [
            {
                "id": c.id,
                "display_name": c.display_name,
                "phone": c.phone,
                "wa_jid": c.wa_jid or "",
                "service_id": c.service_id or "",
                "partner_id": c.partner_id.id if c.partner_id else False,
                "avatar_url": (
                    f"/web/image/res.partner/{c.partner_id.id}/avatar_128"
                    if c.partner_id
                    else False
                ),
                "last_message_date": (
                    c.last_message_date.isoformat() if c.last_message_date else None
                ),
                "last_message_preview": c.last_message_preview or "",
                "unread_count": c.unread_count,
                "active": c.active,
            }
            for c in convs
        ]

    @http.route("/whatsapp/archive", type="json", auth="user")
    def archive_conversation(self, conversation_id, archive=True):
        conv = request.env["whatsapp.conversation"].with_context(active_test=False).browse(int(conversation_id))
        if not conv.exists():
            return {"error": "Conversazione non trovata"}
        conv.active = not archive  # archive=True → active=False
        return {"ok": True, "active": conv.active}

    @http.route("/whatsapp/messages", type="json", auth="user")
    def get_messages(self, conversation_id, limit=50, offset=0):
        msgs = (
            request.env["whatsapp.message"]
            .search(
                [("conversation_id", "=", int(conversation_id))],
                order="timestamp desc",
                limit=int(limit),
                offset=int(offset),
            )
        )
        # Azzera unread
        conv = request.env["whatsapp.conversation"].browse(int(conversation_id))
        if conv.exists():
            conv.unread_count = 0

        return [
            {
                "id": m.id,
                "direction": m.direction,
                "body": m.body,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "state": m.state,
                "author_name": m.author_name or "",
            }
            for m in reversed(msgs)  # chronological order
        ]

    @http.route("/whatsapp/new_conversation", type="json", auth="user")
    def new_conversation(self, phone, partner_id=False):
        phone = phone.strip().replace(" ", "")
        conv = request.env["whatsapp.conversation"].search(
            [("phone", "=", phone)], limit=1
        )
        if not conv:
            vals = {"phone": phone}
            if partner_id:
                vals["partner_id"] = int(partner_id)
            conv = request.env["whatsapp.conversation"].create(vals)
        return {"id": conv.id, "display_name": conv.display_name}

    @http.route("/whatsapp/poll_bridge", type="json", auth="user")
    def poll_bridge(self):
        """Poll manuale dal frontend — riceve messaggi dal bridge."""
        return self._poll_incoming()

    # ------------------------------------------------------------------
    # Incoming message polling (usato dal cron e dal frontend)
    # ------------------------------------------------------------------
    @classmethod
    def _poll_incoming_cron(cls):
        """Chiamato dal cron job."""
        env = http.request.env if http.request else None
        if not env:
            return
        account = env["whatsapp.account"].sudo().get_default_account()
        cls._process_incoming(account, env)

    def _poll_incoming(self):
        account = self._get_account()
        return self._process_incoming(account, request.env)

    @staticmethod
    def _process_incoming(account, env):
        data = account._bridge_get("/messages")
        if not data:
            return []

        created = []
        Conversation = env["whatsapp.conversation"].sudo()
        Message = env["whatsapp.message"].sudo()

        for msg in data:
            jid = msg.get("from", "")
            if not jid or msg.get("isGroup"):
                continue

            # Evita duplicati
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
            if ts:
                dt = datetime.fromtimestamp(int(ts))
            else:
                dt = datetime.now()

            new_msg = Message.create({
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
            created.append({
                "id": new_msg.id,
                "conversation_id": conv.id,
                "body": new_msg.body,
                "direction": "in",
                "timestamp": dt.isoformat(),
            })

        return created
