from odoo import api, fields, models


class Qs2AppDistributionList(models.Model):
    """Custom distribution list: a named set of users used as a send target."""

    _name = "qs2.app.distribution.list"
    _description = "Lista di distribuzione App"
    _order = "name"

    name = fields.Char(string="Nome", required=True)
    active = fields.Boolean(default=True)
    user_ids = fields.Many2many(
        "res.users",
        "qs2_app_dist_list_user_rel",
        "list_id",
        "user_id",
        string="Membri",
    )
    member_count = fields.Integer(string="N. membri", compute="_compute_member_count")
    note = fields.Text(string="Note")

    @api.depends("user_ids")
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.user_ids)
