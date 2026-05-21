from odoo import fields, models


class Qs2Ad(models.Model):
    _name = "qs2.ad"
    _description = "Inserzione"
    _order = "create_date desc"

    name = fields.Char(string="Nome", required=True)
    media_plan_id = fields.Many2one(
        "qs2.media.plan", string="Piano Media", required=True, index=True,
    )
    media_type = fields.Selection(
        [
            ("image", "Foto"),
            ("video", "Video"),
            ("text", "Testo"),
        ],
        string="Tipo Media",
        default="image",
        required=True,
    )
    platform = fields.Selection(
        [
            ("meta", "Meta (Facebook / Instagram)"),
            ("google", "Google Ads"),
            ("tiktok", "TikTok Ads"),
            ("linkedin", "LinkedIn Ads"),
            ("email", "Email Marketing"),
            ("other", "Altro"),
        ],
        string="Piattaforma",
        default="meta",
    )
    image = fields.Binary(string="Immagine / Thumbnail", attachment=True)
    platform_ref = fields.Char(
        string="Riferimento su piattaforma",
        help="ID o codice dell'inserzione sulla piattaforma pubblicitaria",
    )
    url = fields.Char(string="Link")
    active = fields.Boolean(default=True)
    note = fields.Text(string="Note")

    # Campi correlati per comodità nella Kanban
    campaign_id = fields.Many2one(
        related="media_plan_id.campaign_id", store=True, string="Campagna",
    )
    source_id = fields.Many2one(
        related="media_plan_id.source_id", store=True, string="Origine",
    )
    brand_id = fields.Many2one(
        related="media_plan_id.brand_id", store=True, string="Brand",
    )
