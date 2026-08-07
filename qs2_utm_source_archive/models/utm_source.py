# -*- coding: utf-8 -*-
from odoo import fields, models


class UtmSource(models.Model):
    _inherit = "utm.source"

    active = fields.Boolean(
        string="Attivo",
        default=True,
        help="Se disattivato, la sorgente resta valorizzata sui record che la "
        "utilizzano ma non viene piu' proposta nei menu a tendina.",
    )
