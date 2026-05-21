"""Wizard transient per inviare un messaggio WhatsApp partendo da un crm.lead."""

from odoo import api, fields, models
from odoo.exceptions import UserError


class WhatsAppLeadWizard(models.TransientModel):
    _name = "qs2.whatsapp.lead.wizard"
    _description = "Invia WhatsApp da lead CRM"

    lead_id = fields.Many2one("crm.lead", string="Lead", required=True)
    phone = fields.Char(string="Numero destinatario", required=True)
    template_id = fields.Many2one(
        "qs2.whatsapp.template",
        string="Template",
        help="Scegli un template predefinito (configurabili da WhatsApp > Configurazione > Template).",
    )
    body = fields.Text(
        string="Messaggio", required=True,
        help="Puoi modificare il testo prima di inviarlo.",
    )

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id:
            self.body = self.template_id.render(self.lead_id)

    @api.model
    def default_get(self, fields_list):
        """Se viene passato `default_lead_id` (es. dal chatter di crm.lead),
        prepopolo `phone` dal lead — l'utente non deve digitarlo a mano."""
        result = super().default_get(fields_list)
        if "phone" not in result and result.get("lead_id"):
            lead = self.env["crm.lead"].browse(result["lead_id"])
            if lead.exists():
                result["phone"] = lead.phone or (
                    lead.partner_id.phone if lead.partner_id else ""
                )
        return result

    def action_send(self):
        self.ensure_one()
        if not self.phone:
            raise UserError("Manca il numero di telefono del destinatario.")
        Conv = self.env["whatsapp.conversation"]
        Conv.send_message(
            phone=self.phone,
            partner_id=self.lead_id.partner_id.id if self.lead_id.partner_id else None,
            body=self.body,
        )
        # Il send_message crea già un whatsapp.message → l'override di create
        # in whatsapp_message.py lo posta automaticamente nel chatter del lead.
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "WhatsApp",
                "message": f"Messaggio inviato a {self.phone}",
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
