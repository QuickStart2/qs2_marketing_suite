"""Template di messaggi WhatsApp riusabili.

Permette di configurare in anticipo N messaggi tipo (saluto, follow-up,
chiusura, ecc.) che il venditore può selezionare al volo dal wizard di
invio. Supporta segnaposto `{first_name}`, `{partner_name}`, `{user_name}`
che vengono sostituiti al momento dell'invio.
"""

from odoo import fields, models


class WhatsAppTemplate(models.Model):
    _name = "qs2.whatsapp.template"
    _description = "Template messaggio WhatsApp"
    _order = "sequence, id"

    name = fields.Char(required=True, string="Nome template")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    body = fields.Text(
        required=True,
        help="Testo del messaggio. Segnaposto supportati: "
             "{first_name}, {partner_name}, {user_name}.",
    )
    description = fields.Char(
        help="Breve nota interna (non viene inviata).",
    )

    def render(self, lead=None):
        """Sostituisce i segnaposto contestualizzando sul lead se fornito."""
        self.ensure_one()
        body = self.body or ""
        if lead:
            first_name = ""
            if lead.contact_name:
                first_name = lead.contact_name.split()[0]
            elif lead.partner_id and lead.partner_id.name:
                first_name = lead.partner_id.name.split()[0]
            body = body.format(
                first_name=first_name or "",
                partner_name=lead.partner_name or (lead.partner_id.name if lead.partner_id else "") or "",
                user_name=lead.user_id.name if lead.user_id else "",
            )
        return body
