"""Criteri di rating dei lead — configurabili dal cliente.

Widget a stelle 1-5 calcolato in base a una serie di parametri definiti
dal cliente (es: numero verificato, azienda solvibile, ha visto i webinar,
ha scaricato la guida, ...). Ogni criterio ha un peso; il compute
`crm.lead.qs2_rating` somma i pesi dei criteri soddisfatti e mappa il
risultato su una scala 0-5.
"""

import ast
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LeadRatingCriterion(models.Model):
    _name = "qs2.lead.rating.criterion"
    _description = "Criterio di rating lead"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(
        help="Mostrato nel tooltip della scheda lead.",
    )
    weight = fields.Integer(
        default=1, required=True,
        help="Peso del criterio nella somma totale. I criteri pesano in modo "
             "relativo: il rating finale è (somma pesi matchati) / (somma pesi totali) × 5.",
    )

    kind = fields.Selection(
        [
            ("truthy", "Campo valorizzato (truthy)"),
            ("equals", "Campo uguale a valore atteso"),
            ("domain", "Lead matcha domain"),
        ],
        default="truthy", required=True,
    )
    field_name = fields.Char(
        string="Campo crm.lead",
        help="Nome tecnico del campo (es. 'email_from', 'phone', 'qs2_ad_id'). "
             "Usato per i modi 'truthy' ed 'equals'.",
    )
    expected_value = fields.Char(
        help="Valore atteso del campo per i criteri 'equals'.",
    )
    domain = fields.Char(
        string="Domain",
        help="Domain Odoo (es. \"[('expected_revenue', '>', 1000)]\"). "
             "Usato per il modo 'domain'.",
    )

    def _evaluate(self, lead):
        """True se il criterio matcha il lead. Errori → False (loggati)."""
        self.ensure_one()
        try:
            if self.kind == "truthy":
                if not self.field_name:
                    return False
                return bool(getattr(lead, self.field_name, None))
            if self.kind == "equals":
                if not self.field_name:
                    return False
                value = getattr(lead, self.field_name, None)
                # Confronto stringa-safe (su M2O confronta il nome)
                if hasattr(value, "id") and not isinstance(value, str):
                    value = value.display_name if value else ""
                return str(value or "") == (self.expected_value or "")
            if self.kind == "domain":
                if not self.domain:
                    return False
                domain = ast.literal_eval(self.domain)
                return bool(self.env["crm.lead"].search_count(
                    [("id", "=", lead.id)] + domain
                ))
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "Rating criterion '%s' fallito su lead %s: %s",
                self.name, lead.id, exc,
            )
        return False
