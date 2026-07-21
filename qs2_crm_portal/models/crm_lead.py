"""Estende crm.lead per l'accesso portale.

Aggiunge il "Referente portale" (l'utente portale che può vedere/aggiornare il
lead) e la whitelist di campi accessibili dal portale, applicata a livello ORM
tramite `_has_field_access`: fuori sudo e per un utente portale, read/write sono
limitati ai soli campi elencati — anche via RPC diretto, non solo dal controller.
"""

from odoo import api, fields, models, tools

# Campi che un referente portale può MODIFICARE (dati di contatto + la fase,
# cambiata via drag&drop nella pipeline).
CRM_LEAD_PORTAL_WRITABLE_FIELDS = frozenset({
    "contact_name",
    "partner_name",
    "email_from",
    "phone",
    "function",
    "street",
    "street2",
    "city",
    "zip",
    "state_id",
    "country_id",
    "qs2_initiative",
    "stage_id",
})

# Campi che un referente portale può LEGGERE: i modificabili + quelli mostrati
# in pipeline/dettaglio + quelli che l'ORM legge internamente (display_name,
# ordinamento). Tutto ciò che NON è qui è invisibile al portale (anche i dati
# commerciali: expected_revenue, probability, user_id, team_id...).
CRM_LEAD_PORTAL_READABLE_FIELDS = CRM_LEAD_PORTAL_WRITABLE_FIELDS | frozenset({
    "id",
    "name",
    "display_name",
    "type",
    "active",
    "color",
    "priority",
    "tag_ids",
    "create_date",
    "write_date",
    "date_open",
    "company_id",
    "email_normalized",
    "qs2_portal_user_id",
})


class CrmLead(models.Model):
    _inherit = "crm.lead"

    qs2_portal_user_id = fields.Many2one(
        "res.users",
        string="Referente portale",
        domain=[("share", "=", True)],
        index=True,
        tracking=True,
        help="Utente portale che può vedere e aggiornare questo lead "
        "dalla propria area riservata (/my/leads).",
    )

    @api.model
    @tools.ormcache(cache="stable")
    def _portal_accessible_fields(self):
        """(campi leggibili, campi scrivibili) per un utente portale."""
        return CRM_LEAD_PORTAL_READABLE_FIELDS, CRM_LEAD_PORTAL_WRITABLE_FIELDS

    def _has_field_access(self, field, operation):
        if not super()._has_field_access(field, operation):
            return False
        if not self.env.su and self.env.user._is_portal():
            readable, writable = self._portal_accessible_fields()
            if operation == "read":
                return field.name in readable
            if operation == "write":
                return field.name in writable
        return True

    # ------------------------------------------------------------------
    # Blocco propagazione lead → res.partner nel salvataggio portale.
    #
    # email_from e phone sono campi con `inverse` che, scrivendo, riportano il
    # valore su partner_id.email / partner_id.phone. La write del portale è in
    # sudo (serve perché il ricalcolo legge partner_id, non leggibile dal
    # portale), quindi quell'inverse scriverebbe su res.partner ignorando ACL e
    # record rule: un referente potrebbe modificare l'email/telefono di un
    # contatto su cui non ha diritti (fino al dirottamento di un reset password
    # se quel contatto è legato a un utente). Con il flag di context
    # `qs2_portal_no_partner_sync` i due gate del core ritornano False: il valore
    # resta salvato sul lead (colonna store=True) ma NON tocca il partner.
    # ------------------------------------------------------------------
    def _get_partner_email_update(self, force_void=True):
        if self.env.context.get("qs2_portal_no_partner_sync"):
            return False
        return super()._get_partner_email_update(force_void=force_void)

    def _get_partner_phone_update(self, force_void=True):
        if self.env.context.get("qs2_portal_no_partner_sync"):
            return False
        return super()._get_partner_phone_update(force_void=force_void)


# Campi di crm.stage leggibili dal portale: quelli che servono a pipeline e
# statusbar. Esclude `requirements` ("internal requirements for this stage") e
# gli altri campi di configurazione, che un portale non deve poter leggere via
# RPC. Il controller legge le fasi in sudo, quindi i template non sono toccati.
CRM_STAGE_PORTAL_READABLE_FIELDS = frozenset({
    "id", "name", "display_name", "sequence", "is_won", "fold", "color",
})


class CrmStage(models.Model):
    _inherit = "crm.stage"

    def _has_field_access(self, field, operation):
        if not super()._has_field_access(field, operation):
            return False
        if operation == "read" and not self.env.su and self.env.user._is_portal():
            return field.name in CRM_STAGE_PORTAL_READABLE_FIELDS
        return True
