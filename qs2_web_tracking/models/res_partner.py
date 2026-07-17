import secrets

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    qs2_tracking_code = fields.Char(
        string="Tracking Code",
        size=12,
        copy=False,
        index=True,
        readonly=True,
        help="Codice univoco di 12 caratteri: A-Z, 0-9, '-' e '_' (base64url in maiuscolo)",
    )
    qs2_visit_ids = fields.One2many(
        "qs2.visit", "partner_id", string="Visite Web",
    )
    qs2_visit_count = fields.Integer(
        string="N. Visite", compute="_compute_visit_count", store=True,
    )
    # Milestone raggiunte tramite le regole pattern URL → milestone configurate
    # in qs2.tracking.rule. Su questa relazione si appoggia il cliente per le
    # automazioni downstream (WhatsApp/email/SMS) via base.automation.
    qs2_milestone_ids = fields.Many2many(
        "qs2.tracking.milestone",
        "qs2_partner_milestone_rel",
        "partner_id", "milestone_id",
        string="Milestone tracking",
    )
    qs2_milestone_count = fields.Integer(
        string="N° Milestone",
        compute="_compute_qs2_milestone_count",
        store=True,
    )

    @api.depends("qs2_milestone_ids")
    def _compute_qs2_milestone_count(self):
        for rec in self:
            rec.qs2_milestone_count = len(rec.qs2_milestone_ids)

    @api.depends("qs2_visit_ids")
    def _compute_visit_count(self):
        for rec in self:
            rec.qs2_visit_count = len(rec.qs2_visit_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("qs2_tracking_code"):
                vals["qs2_tracking_code"] = self._generate_tracking_code()
        return super().create(vals_list)

    def _generate_tracking_code(self):
        """Genera un codice univoco di 12 caratteri (base64url in maiuscolo).

        L'alfabeto è A-Z, 0-9, '-' e '_': non è alfanumerico puro, ma è
        URL-safe, che è ciò che serve al parametro ?track=CODE.
        """
        while True:
            code = secrets.token_urlsafe(9)[:12].upper()
            if not self.search([("qs2_tracking_code", "=", code)], limit=1):
                return code

    _sql_constraints = [
        (
            "qs2_tracking_code_unique",
            "UNIQUE(qs2_tracking_code)",
            "Il codice di tracking deve essere univoco!",
        ),
    ]

    def action_view_visits(self):
        self.ensure_one()
        return {
            "name": "Visite Web",
            "type": "ir.actions.act_window",
            "res_model": "qs2.visit",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
