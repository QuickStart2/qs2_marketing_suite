from odoo import api, fields, models


MONTH_SELECTION = [
    ("01", "Gennaio"), ("02", "Febbraio"), ("03", "Marzo"),
    ("04", "Aprile"), ("05", "Maggio"), ("06", "Giugno"),
    ("07", "Luglio"), ("08", "Agosto"), ("09", "Settembre"),
    ("10", "Ottobre"), ("11", "Novembre"), ("12", "Dicembre"),
]

YEAR_SELECTION = [(str(y), str(y)) for y in range(2020, 2036)]


class Qs2MediaPlan(models.Model):
    _name = "qs2.media.plan"
    _description = "Piano Media"
    _order = "year desc, month desc, campaign_id"
    _rec_name = "display_name"

    # ------------------------------------------------------------------
    # Dimensioni
    # ------------------------------------------------------------------
    campaign_id = fields.Many2one(
        "utm.campaign", string="Campagna", required=True, index=True,
    )
    source_id = fields.Many2one(
        "utm.source", string="Origine", required=True, index=True,
    )
    medium_id = fields.Many2one(
        "utm.medium", string="Mezzo",
    )
    brand_id = fields.Many2one(
        "qs2.brand", string="Brand", index=True,
    )
    year = fields.Selection(
        YEAR_SELECTION, string="Anno", required=True, index=True,
        default=lambda self: str(fields.Date.today().year),
    )
    month = fields.Selection(
        MONTH_SELECTION, string="Mese", required=True,
        default=lambda self: str(fields.Date.today().month).zfill(2),
    )
    company_id = fields.Many2one(
        "res.company", string="Azienda",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Valuta",
        default=lambda self: self.env.company.currency_id,
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string="Note")

    # ------------------------------------------------------------------
    # Inserzioni e Lead collegati
    # ------------------------------------------------------------------
    ad_ids = fields.One2many("qs2.ad", "media_plan_id", string="Inserzioni")
    ad_count = fields.Integer(compute="_compute_ad_count", string="N. Inserzioni")
    crm_lead_ids = fields.One2many(
        "crm.lead", "qs2_media_plan_id", string="Lead collegati",
    )

    # ------------------------------------------------------------------
    # Metriche input — Awareness
    # ------------------------------------------------------------------
    impressions = fields.Integer(string="Impressions")
    clicks = fields.Integer(string="Click")

    # ------------------------------------------------------------------
    # Metriche input — Costo
    # ------------------------------------------------------------------
    cost = fields.Monetary(string="Costo", currency_field="currency_id")

    # ------------------------------------------------------------------
    # Metriche auto da CRM
    # ------------------------------------------------------------------
    lead_count = fields.Integer(
        string="Lead", compute="_compute_crm_metrics", store=True,
    )
    conversions = fields.Integer(
        string="Conversioni", compute="_compute_crm_metrics", store=True,
        help="Lead vinti (stage is_won)",
    )
    revenue = fields.Monetary(
        string="Ricavo", compute="_compute_crm_metrics", store=True,
        currency_field="currency_id",
        help="Somma expected_revenue dei lead vinti",
    )

    # ------------------------------------------------------------------
    # Metriche calcolate
    # ------------------------------------------------------------------
    ctr = fields.Float(
        string="CTR %", compute="_compute_awareness", store=True, digits=(6, 2),
        help="Click-Through Rate = Click / Impressions * 100",
    )
    cpm = fields.Monetary(
        string="CPM", compute="_compute_awareness", store=True,
        currency_field="currency_id",
        help="Costo per 1000 Impressions",
    )
    cpc = fields.Monetary(
        string="CPC", compute="_compute_acquisition", store=True,
        currency_field="currency_id",
        help="Costo per Click",
    )
    cpl = fields.Monetary(
        string="CPL", compute="_compute_acquisition", store=True,
        currency_field="currency_id",
        help="Costo per Lead",
    )
    conversion_rate = fields.Float(
        string="Conv. Rate %", compute="_compute_conversion", store=True,
        digits=(6, 2),
        help="Tasso di conversione = Conversioni / Lead * 100",
    )
    cpa = fields.Monetary(
        string="CPA", compute="_compute_conversion", store=True,
        currency_field="currency_id",
        help="Costo per Acquisizione (conversione)",
    )
    roas = fields.Float(
        string="ROAS", compute="_compute_conversion", store=True,
        digits=(6, 2),
        help="Return on Ad Spend = Ricavo / Costo",
    )

    # ------------------------------------------------------------------
    # Display name
    # ------------------------------------------------------------------
    display_name = fields.Char(
        compute="_compute_display_name", store=True,
    )

    _sql_constraints = [
        (
            "unique_plan",
            "unique(campaign_id, source_id, medium_id, brand_id, year, month, company_id)",
            "Esiste già un piano media per questa combinazione.",
        ),
    ]

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("ad_ids")
    def _compute_ad_count(self):
        for rec in self:
            rec.ad_count = len(rec.ad_ids)

    @api.depends(
        "crm_lead_ids",
        "crm_lead_ids.stage_id",
        "crm_lead_ids.stage_id.is_won",
        "crm_lead_ids.expected_revenue",
    )
    def _compute_crm_metrics(self):
        for rec in self:
            leads = rec.crm_lead_ids
            rec.lead_count = len(leads)
            won = leads.filtered(lambda l: l.stage_id.is_won)
            rec.conversions = len(won)
            rec.revenue = sum(won.mapped("expected_revenue"))

    def action_open_ads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Inserzioni",
            "res_model": "qs2.ad",
            "view_mode": "kanban,list,form",
            "domain": [("media_plan_id", "=", self.id)],
            "context": {"default_media_plan_id": self.id},
        }

    def action_open_leads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Lead",
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "domain": [("qs2_media_plan_id", "=", self.id)],
        }

    @api.depends("campaign_id.name", "source_id.name", "month", "year")
    def _compute_display_name(self):
        month_map = dict(MONTH_SELECTION)
        for rec in self:
            parts = [
                rec.campaign_id.name or "",
                rec.source_id.name or "",
            ]
            if rec.month and rec.year:
                parts.append(f"{month_map.get(rec.month, rec.month)} {rec.year}")
            rec.display_name = " - ".join(filter(None, parts))

    @api.depends("impressions", "clicks", "cost")
    def _compute_awareness(self):
        for rec in self:
            rec.ctr = (rec.clicks / rec.impressions * 100) if rec.impressions else 0
            rec.cpm = (rec.cost / rec.impressions * 1000) if rec.impressions else 0

    @api.depends("cost", "clicks", "lead_count")
    def _compute_acquisition(self):
        for rec in self:
            rec.cpc = (rec.cost / rec.clicks) if rec.clicks else 0
            rec.cpl = (rec.cost / rec.lead_count) if rec.lead_count else 0

    @api.depends("lead_count", "conversions", "cost", "revenue")
    def _compute_conversion(self):
        for rec in self:
            rec.conversion_rate = (
                (rec.conversions / rec.lead_count * 100) if rec.lead_count else 0
            )
            rec.cpa = (rec.cost / rec.conversions) if rec.conversions else 0
            rec.roas = (rec.revenue / rec.cost) if rec.cost else 0
