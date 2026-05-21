"""Milestone di tracking — eventi significativi che un contatto può raggiungere
visitando determinate URL (es. "Visto Webinar 1", "Scaricato listino", ecc.).

Si configurano in 2 passi:
  1) Crea le milestone in `qs2.tracking.milestone` (es. "Visto Webinar 1")
  2) Crea regole in `qs2.tracking.rule` che mappano un pattern URL → milestone
     (es. url contiene "/webinar-1" → milestone "Visto Webinar 1")

Quando arriva una nuova `qs2.visit`, le regole vengono applicate e le milestone
matchate vengono aggiunte a `res.partner.qs2_milestone_ids`. Le automazioni
downstream (WhatsApp, email, ecc.) si configurano con `base.automation` su
`res.partner` filtrate per la presenza di milestone specifiche.
"""

from odoo import fields, models


class TrackingMilestone(models.Model):
    _name = "qs2.tracking.milestone"
    _description = "Milestone di tracking lead"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()
    color = fields.Integer(default=0)
    partner_count = fields.Integer(
        compute="_compute_partner_count",
        string="N° partner che l'hanno raggiunta",
    )

    _sql_constraints = [
        ("name_unique", "UNIQUE(name)", "Esiste già una milestone con questo nome."),
    ]

    def _compute_partner_count(self):
        Partner = self.env["res.partner"]
        for milestone in self:
            milestone.partner_count = Partner.search_count(
                [("qs2_milestone_ids", "in", milestone.id)]
            )
