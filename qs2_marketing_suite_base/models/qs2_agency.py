from odoo import fields, models


class Qs2Agency(models.Model):
    _name = "qs2.agency"
    _description = "Agenzia Marketing"
    _order = "name"

    name = fields.Char(string="Nome", required=True)
    logo = fields.Binary(string="Logo", attachment=True)
    phone = fields.Char(string="Telefono")
    email = fields.Char(string="Email")
    website = fields.Char(string="Sito web")
    active = fields.Boolean(default=True)
    note = fields.Text(string="Note")

    _sql_constraints = [
        ("name_unique", "unique(name)", "Esiste già un'agenzia con questo nome."),
    ]
