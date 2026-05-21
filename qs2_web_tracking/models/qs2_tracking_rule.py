"""Regole pattern URL → milestone.

Ogni regola specifica:
  - un pattern (substring oppure regex)
  - una milestone da assegnare al partner quando il pattern matcha la URL

Esempio: pattern "/webinar-1" → milestone "Visto Webinar 1"
"""

import re

from odoo import fields, models


class TrackingRule(models.Model):
    _name = "qs2.tracking.rule"
    _description = "Regola pattern URL → milestone"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    url_pattern = fields.Char(
        required=True,
        help="Substring (default) o regex (se 'Regex' è True). "
             "Es. '/webinar-1' oppure '/webinar-[0-9]+'.",
    )
    is_regex = fields.Boolean(string="Regex", default=False)
    milestone_id = fields.Many2one(
        "qs2.tracking.milestone",
        string="Milestone da assegnare",
        required=True,
        ondelete="cascade",
    )

    def matches(self, url):
        """True se questa regola matcha l'URL."""
        self.ensure_one()
        if not url or not self.url_pattern:
            return False
        if self.is_regex:
            try:
                return bool(re.search(self.url_pattern, url))
            except re.error:
                return False
        return self.url_pattern in url
