import logging

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_EMPTY_HTML = ("", "<p></p>", "<p><br></p>", "<p><br/></p>", "<br>", "<br/>", "false")


class Qs2AppMessage(models.Model):
    """Mini mail client: compose a message and dispatch it to app users.

    Dispatching posts a ``mail.message`` on this record with the dedicated
    "Messaggio verso App" subtype and creates one ``mail.notification`` per
    recipient on the ``app`` channel. The external middleware delivers them and
    flips each notification to ``sent``.

    Recipients can be **internal or portal** users, picked one-off or through a
    custom distribution list. Sending can be immediate or **scheduled**: a
    scheduled message is dispatched by the ``ir.cron`` only once its
    ``scheduled_date`` is due, so recipients are resolved at the actual send
    time.
    """

    _name = "qs2.app.message"
    _description = "Messaggio verso App"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Oggetto", required=True, tracking=True)
    body = fields.Html(string="Messaggio", sanitize_style=True)
    author_user_id = fields.Many2one(
        "res.users",
        string="Mittente",
        default=lambda self: self.env.user,
        readonly=True,
        copy=False,
    )

    recipient_mode = fields.Selection(
        [("user", "Utente singolo"), ("list", "Lista di distribuzione")],
        string="Invia a",
        default="user",
        required=True,
    )
    target_user_id = fields.Many2one(
        "res.users",
        string="Utente",
        help="Puoi scegliere un utente interno oppure un utente del portale.",
    )
    target_list_id = fields.Many2one(
        "qs2.app.distribution.list", string="Lista di distribuzione"
    )

    recipient_partner_ids = fields.Many2many(
        "res.partner",
        "qs2_app_message_partner_rel",
        "message_id",
        "partner_id",
        string="Destinatari",
        readonly=True,
        copy=False,
    )

    scheduled_date = fields.Datetime(
        string="Programma invio",
        copy=False,
        help="Se valorizzato, il messaggio viene consegnato solo a partire da "
             "questa data/ora (invio differito gestito da un'attività pianificata).",
    )

    state = fields.Selection(
        [("draft", "Bozza"), ("scheduled", "Programmato"), ("sent", "Inviato")],
        string="Stato",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    app_message_id = fields.Many2one(
        "mail.message", string="Messaggio pubblicato", readonly=True, copy=False
    )
    sent_date = fields.Datetime(string="Data invio", readonly=True, copy=False)

    recipient_count = fields.Integer(string="N. destinatari", compute="_compute_delivery")
    delivered_count = fields.Integer(string="Consegnati", compute="_compute_delivery")
    delivery_state = fields.Selection(
        [
            ("none", "—"),
            ("pending", "In attesa"),
            ("partial", "Parziale"),
            ("delivered", "Consegnato"),
        ],
        string="Consegna",
        compute="_compute_delivery",
    )

    @api.depends(
        "app_message_id",
        "app_message_id.notification_ids.notification_status",
        "app_message_id.notification_ids.notification_type",
    )
    def _compute_delivery(self):
        for rec in self:
            notifs = rec.app_message_id.notification_ids.filtered(
                lambda n: n.notification_type == "app"
            )
            total = len(notifs)
            done = len(notifs.filtered(lambda n: n.notification_status == "sent"))
            rec.recipient_count = total
            rec.delivered_count = done
            if not total:
                rec.delivery_state = "none"
            elif done == 0:
                rec.delivery_state = "pending"
            elif done < total:
                rec.delivery_state = "partial"
            else:
                rec.delivery_state = "delivered"

    @api.onchange("recipient_mode")
    def _onchange_recipient_mode(self):
        if self.recipient_mode == "user":
            self.target_list_id = False
        else:
            self.target_user_id = False

    def _resolve_recipient_partners(self):
        """Snapshot the recipient partners at send time (internal or portal)."""
        self.ensure_one()
        if self.recipient_mode == "user":
            users = self.target_user_id
        else:
            users = self.target_list_id.user_ids
        users = users.filtered(lambda u: u.active)
        return users.partner_id

    def _validate_ready(self):
        """Validate that the message can be sent (recipient + body present)."""
        self.ensure_one()
        if self.recipient_mode == "user" and not self.target_user_id:
            raise UserError(_("Seleziona l'utente destinatario."))
        if self.recipient_mode == "list" and not self.target_list_id:
            raise UserError(_("Seleziona la lista di distribuzione."))
        if (self.body or "").strip().lower() in _EMPTY_HTML:
            raise UserError(_("Il corpo del messaggio è vuoto."))

    def _dispatch(self):
        """Post the message and create the app notifications. Snapshot is taken now."""
        self.ensure_one()
        if self.state == "sent":
            raise UserError(_("Questo messaggio è già stato inviato."))
        self._validate_ready()
        partners = self._resolve_recipient_partners()
        if not partners:
            raise UserError(
                _("Nessun destinatario valido per il target selezionato.")
            )

        subtype = self.env.ref("qs2_app_message.mt_app_message")
        # Post WITHOUT partner_ids and on a record with no followers: no inbox/email
        # notification is auto-created. We then create our own 'app' notifications.
        message = self.message_post(
            body=self.body,
            subject=self.name,
            message_type="notification",
            subtype_id=subtype.id,
        )
        self.env["mail.notification"].sudo().create([
            {
                "mail_message_id": message.id,
                "res_partner_id": partner.id,
                "author_id": message.author_id.id,
                "notification_type": "app",
                "notification_status": "ready",
            }
            for partner in partners
        ])
        # Record the recipients on the message for display (no re-notification).
        message.sudo().write({"partner_ids": [Command.set(partners.ids)]})
        self.write({
            "state": "sent",
            "sent_date": fields.Datetime.now(),
            "app_message_id": message.id,
            "recipient_partner_ids": [Command.set(partners.ids)],
        })
        return message

    def action_send(self):
        """Invia ora (immediato)."""
        self.ensure_one()
        self._dispatch()
        return True

    def action_schedule(self):
        """Programma l'invio: verrà consegnato dal cron alla 'scheduled_date'."""
        self.ensure_one()
        if self.state == "sent":
            raise UserError(_("Questo messaggio è già stato inviato."))
        if not self.scheduled_date:
            raise UserError(
                _("Imposta la data in 'Programma invio' prima di programmare.")
            )
        self._validate_ready()
        if not self._resolve_recipient_partners():
            raise UserError(
                _("Nessun destinatario valido per il target selezionato.")
            )
        self.write({"state": "scheduled"})
        return True

    def action_cancel_schedule(self):
        """Riporta in bozza un messaggio programmato (per modificarlo)."""
        self.ensure_one()
        if self.state != "scheduled":
            raise UserError(_("Solo i messaggi programmati possono essere annullati."))
        self.write({"state": "draft"})
        return True

    @api.model
    def _cron_dispatch_scheduled(self):
        """Dispatch every scheduled message whose time has come."""
        now = fields.Datetime.now()
        due = self.search([
            ("state", "=", "scheduled"),
            ("scheduled_date", "<=", now),
        ])
        for rec in due:
            try:
                with self.env.cr.savepoint():
                    rec._dispatch()
            except Exception:
                _logger.exception(
                    "Invio programmato fallito per qs2.app.message id=%s", rec.id
                )
        return True

    def action_view_notifications(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Consegne App"),
            "res_model": "mail.notification",
            "view_mode": "list,form",
            "views": [
                (self.env.ref("qs2_app_message.mail_notification_app_view_list").id, "list"),
                (False, "form"),
            ],
            "domain": [
                ("mail_message_id", "=", self.app_message_id.id),
                ("notification_type", "=", "app"),
            ],
            "context": {"create": False},
        }
