from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    whatsapp_conversation_ids = fields.One2many(
        "whatsapp.conversation", "partner_id", string="Conversazioni WhatsApp"
    )
    whatsapp_conversation_count = fields.Integer(
        compute="_compute_whatsapp_conversation_count"
    )

    def _compute_whatsapp_conversation_count(self):
        for partner in self:
            partner.whatsapp_conversation_count = len(
                partner.whatsapp_conversation_ids
            )

    def action_open_whatsapp(self):
        """Apri o crea una conversazione WhatsApp con questo contatto."""
        self.ensure_one()
        phone = self.phone
        if not phone:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "WhatsApp",
                    "message": "Nessun numero di telefono configurato per questo contatto.",
                    "type": "warning",
                },
            }

        phone = phone.strip().replace(" ", "")
        conv = self.env["whatsapp.conversation"].search(
            [("phone", "=", phone)], limit=1
        )
        if not conv:
            conv = self.env["whatsapp.conversation"].create({
                "phone": phone,
                "partner_id": self.id,
            })

        return {
            "type": "ir.actions.client",
            "tag": "qs2_whatsapp_bridge.chat",
            "params": {"conversation_id": conv.id},
        }
