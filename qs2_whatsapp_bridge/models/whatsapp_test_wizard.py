from odoo import api, fields, models
from odoo.exceptions import UserError


class WhatsAppTestMessageWizard(models.TransientModel):
    _name = "whatsapp.test.message.wizard"
    _description = "WhatsApp Test Message"

    account_id = fields.Many2one("whatsapp.account", required=True)
    phone = fields.Char(string="Numero destinatario", required=True,
                        help="Numero con prefisso internazionale (es. +39328...)")
    message = fields.Text(string="Messaggio", required=True,
                          default="Messaggio di test da Odoo!")

    def action_send(self):
        self.ensure_one()
        result = self.account_id._bridge_post(
            "/send", {"to": self.phone, "message": self.message}
        )
        if not result or not result.get("ok"):
            error = result.get("error", "Errore sconosciuto") if result else "Bridge non raggiungibile"
            raise UserError(f"Invio fallito: {error}")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "WhatsApp",
                "message": f"Messaggio inviato a {self.phone}!",
                "type": "success",
            },
        }
