from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    qs2_tracking_code = fields.Char(
        related="partner_id.qs2_tracking_code",
        string="Tracking Code",
        readonly=True,
        store=True,
    )
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_phone_vals(vals)
            if not vals.get("partner_id"):
                vals["partner_id"] = self._ensure_partner(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._normalize_phone_vals(vals)
        return super().write(vals)

    def _ensure_partner(self, vals):
        """Crea un contatto a partire dai dati del lead se non specificato."""
        partner_name = (
            vals.get("partner_name")
            or vals.get("contact_name")
            or vals.get("name", "")
        )
        partner_vals = {"name": partner_name, "type": "contact"}
        if vals.get("email_from"):
            partner_vals["email"] = vals["email_from"]
        if vals.get("phone"):
            partner_vals["phone"] = vals["phone"]
        partner = self.env["res.partner"].create(partner_vals)
        return partner.id

    def _normalize_phone_vals(self, vals):
        """Normalizza phone in formato E164 nei vals prima del salvataggio."""
        for fname in ("phone",):
            number = vals.get(fname)
            if not number:
                continue
            country = self._get_country_for_phone(vals)
            formatted = self._phone_format(
                fname=fname,
                number=number,
                country=country,
                force_format="E164",
                raise_exception=False,
            )
            if formatted:
                vals[fname] = formatted

    def _get_country_for_phone(self, vals):
        """Ricava il country dai vals o dal record per la normalizzazione."""
        country_id = vals.get("country_id")
        if country_id:
            return self.env["res.country"].browse(country_id)
        if self:
            return self[:1].country_id or self.env.company.country_id
        return self.env.company.country_id
