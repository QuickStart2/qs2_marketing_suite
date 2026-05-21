from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    qs2_ad_id = fields.Many2one(
        "qs2.ad", string="Inserzione",
        help="Inserzione pubblicitaria collegata a questo lead",
        index=True,
    )
    qs2_media_plan_id = fields.Many2one(
        related="qs2_ad_id.media_plan_id",
        string="Piano Media",
        store=True,
    )
    qs2_brand_id = fields.Many2one(
        "qs2.brand",
        string="Brand",
        compute="_compute_qs2_brand_id",
        store=True,
        readonly=False,
        index=True,
        help=(
            "Brand del lead. Se l'inserzione collegata ha un brand, viene "
            "popolato in automatico, ma resta modificabile manualmente "
            "(o scrivibile dal webhook quando il lead non arriva da un ad)."
        ),
    )

    @api.depends("qs2_ad_id.brand_id")
    def _compute_qs2_brand_id(self):
        # compute "soft": valorizza dal brand dell'ad SOLO se l'utente non
        # ha già messo un brand manualmente. Questo evita che il cambio di ad
        # sovrascriva un brand già impostato dal webhook o dall'utente.
        for lead in self:
            if lead.qs2_ad_id and lead.qs2_ad_id.brand_id and not lead.qs2_brand_id:
                lead.qs2_brand_id = lead.qs2_ad_id.brand_id
    qs2_agency_id = fields.Many2one(
        "qs2.agency", string="Agenzia",
        help="Agenzia marketing che ha generato il lead",
        index=True,
    )
    qs2_initiative = fields.Char(
        string="Iniziativa",
        help="Nome dell'iniziativa o evento (es. Webinar Maggio, Fiera Milano)",
    )
    # Immagine/frame della creatività che il prospect ha visualizzato — mostrata
    # nel form lead per dare al venditore il pain point esatto su cui aprire la chiamata.
    qs2_ad_image = fields.Binary(
        related="qs2_ad_id.image",
        string="Frame creatività",
        readonly=True,
    )

    # Rating 0-5 stelle calcolato dai criteri configurabili in qs2.lead.rating.criterion.
    # Selection (non Integer) per essere usato con widget="priority" nel form.
    qs2_rating = fields.Selection(
        [("0", "0"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")],
        string="Rating QS2",
        compute="_compute_qs2_rating",
        store=True,
        default="0",
    )
    qs2_rating_matched_ids = fields.Many2many(
        "qs2.lead.rating.criterion",
        string="Criteri soddisfatti",
        compute="_compute_qs2_rating",
        store=True,
    )

    @api.depends(
        "email_from", "phone", "partner_name", "city", "state_id", "country_id",
        "qs2_ad_id", "qs2_media_plan_id", "qs2_brand_id", "qs2_initiative",
        "expected_revenue", "won_status", "stage_id",
    )
    def _compute_qs2_rating(self):
        criteria = self.env["qs2.lead.rating.criterion"].search([])
        total_weight = sum(c.weight for c in criteria) or 0
        for lead in self:
            if not criteria or total_weight <= 0:
                lead.qs2_rating = "0"
                lead.qs2_rating_matched_ids = [(5, 0, 0)]
                continue
            matched = criteria.filtered(lambda c: c._evaluate(lead))
            matched_weight = sum(c.weight for c in matched)
            stars = round(matched_weight / total_weight * 5)
            stars = max(0, min(5, stars))
            lead.qs2_rating = str(stars)
            lead.qs2_rating_matched_ids = [(6, 0, matched.ids)]
