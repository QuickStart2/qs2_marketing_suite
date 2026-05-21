from odoo import api, fields, models


class Qs2Visit(models.Model):
    _name = "qs2.visit"
    _description = "Visita web contatto"
    _order = "timestamp desc"

    partner_id = fields.Many2one(
        "res.partner", string="Contatto",
        required=True, ondelete="cascade", index=True,
    )
    url = fields.Char(string="URL", required=True)
    timestamp = fields.Datetime(
        string="Timestamp", required=True, default=fields.Datetime.now,
    )
    ip_address = fields.Char(string="IP Address")
    user_agent = fields.Text(string="User Agent")
    referer = fields.Char(string="Referer")
    session_id = fields.Char(string="Session ID", index=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Applica le regole pattern URL → milestone. Una visita può triggerare
        # più milestone se più regole matchano la stessa URL.
        rules = self.env["qs2.tracking.rule"].sudo().search([])
        if rules:
            for visit in records:
                matched = rules.filtered(lambda r: r.matches(visit.url))
                if matched and visit.partner_id:
                    visit.partner_id.sudo().qs2_milestone_ids = [
                        (4, m.id) for m in matched.milestone_id
                    ]
        return records
