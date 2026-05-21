"""Regole di routing dei lead in ingresso dai webhook.

Tabella di regole configurabile che assegna automaticamente i lead in
ingresso a un venditore o team in base a CAP, paese, provincia, lingua o
sorgente — senza dover hard-codare user_id nel controller.
"""

from odoo import api, fields, models


class LeadRoutingRule(models.Model):
    _name = "qs2.lead.routing.rule"
    _description = "Regola di routing lead da webhook"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Condizioni — applicate in AND. Vuoto = non filtra su quel campo.
    country_ids = fields.Many2many(
        "res.country", string="Paesi",
        help="La regola scatta solo per lead in questi paesi.",
    )
    state_ids = fields.Many2many(
        "res.country.state", string="Province/Regioni",
        help="La regola scatta solo per lead in queste province.",
    )
    zip_pattern = fields.Char(
        string="Pattern CAP",
        help="Es. '20*' per CAP che iniziano con 20. Vuoto = non filtra.",
    )
    lang = fields.Selection(
        selection="_lang_selection", string="Lingua",
        help="Lingua del contatto (it_IT, en_US, ...). Vuoto = non filtra.",
    )
    source_ids = fields.Many2many(
        "utm.source", string="Origini UTM",
    )
    brand_ids = fields.Many2many(
        "qs2.brand", string="Brand",
    )
    initiative_pattern = fields.Char(
        string="Pattern iniziativa",
        help="Es. 'Webinar*' per iniziative che iniziano con Webinar.",
    )

    # Target
    user_id = fields.Many2one(
        "res.users", string="Assegna a", required=True,
    )
    team_id = fields.Many2one(
        "crm.team", string="Team commerciale",
    )

    @api.model
    def _lang_selection(self):
        return self.env["res.lang"].get_installed()

    @api.model
    def route(self, vals):
        """Trova la prima regola che matcha e ritorna (user_id, team_id).

        `vals` è il dict che sta per essere passato a crm.lead.create.
        Ritorna `(False, False)` se nessuna regola matcha — il chiamante
        può fare il proprio fallback (es. system parameter).
        """
        rules = self.search([])
        for rule in rules:
            if rule._matches(vals):
                return rule.user_id.id, rule.team_id.id or False
        return False, False

    def _matches(self, vals):
        self.ensure_one()
        if self.country_ids and vals.get("country_id") not in self.country_ids.ids:
            return False
        if self.state_ids and vals.get("state_id") not in self.state_ids.ids:
            return False
        if self.zip_pattern:
            zip_val = (vals.get("zip") or "").strip()
            if not _match_glob(zip_val, self.zip_pattern):
                return False
        if self.lang and vals.get("lang") != self.lang:
            return False
        if self.source_ids and vals.get("source_id") not in self.source_ids.ids:
            return False
        if self.brand_ids:
            brand_id = vals.get("qs2_brand_id")
            # qs2_brand_id sul lead è related da qs2_ad_id — su create potrebbe
            # non essere ancora valorizzato; verifico anche x_studio_brand legacy.
            if not brand_id:
                brand_id = vals.get("x_studio_brand")
            if brand_id not in self.brand_ids.ids:
                return False
        if self.initiative_pattern:
            iniz = vals.get("qs2_initiative") or vals.get("x_studio_iniziativa") or ""
            if not _match_glob(iniz, self.initiative_pattern):
                return False
        return True


def _match_glob(value, pattern):
    """Match glob semplice: '*' = qualsiasi suffisso/prefisso, no regex."""
    if not pattern:
        return True
    if not value:
        return False
    pattern = pattern.strip()
    value = value.strip()
    if pattern.startswith("*") and pattern.endswith("*"):
        return pattern.strip("*").lower() in value.lower()
    if pattern.startswith("*"):
        return value.lower().endswith(pattern[1:].lower())
    if pattern.endswith("*"):
        return value.lower().startswith(pattern[:-1].lower())
    return value.lower() == pattern.lower()
