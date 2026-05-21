from odoo import api, fields, models


class Qs2Brand(models.Model):
    _name = "qs2.brand"
    _description = "Brand"
    _order = "name"

    name = fields.Char(string="Nome", required=True)
    logo = fields.Binary(string="Logo", attachment=True)
    active = fields.Boolean(default=True)
    note = fields.Text(string="Note")
    media_plan_ids = fields.One2many(
        "qs2.media.plan", "brand_id", string="Piani Media"
    )
    media_plan_count = fields.Integer(
        compute="_compute_media_plan_count", string="N. Piani"
    )

    _sql_constraints = [
        ("name_unique", "unique(name)", "Esiste già un brand con questo nome."),
    ]

    @api.depends("media_plan_ids")
    def _compute_media_plan_count(self):
        for rec in self:
            rec.media_plan_count = len(rec.media_plan_ids)
