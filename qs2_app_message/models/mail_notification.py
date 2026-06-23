from odoo import api, fields, models


class MailNotification(models.Model):
    """Extend the native per-recipient notification with an ``app`` channel.

    Each app message produces one ``mail.notification`` row per recipient with
    ``notification_type = 'app'`` and ``notification_status = 'ready'``. The
    external middleware reads the pending rows and writes ``'sent'`` once the
    message has been delivered to the app, reusing Odoo's native delivery state
    machine instead of a parallel custom field.
    """

    _inherit = "mail.notification"

    notification_type = fields.Selection(
        selection_add=[("app", "App")],
        ondelete={"app": "cascade"},
    )

    @api.model
    def app_fetch_pending(self, limit=100):
        """RPC helper for the external middleware.

        Returns the app notifications still to be delivered, newest last.
        Runs with the caller's access rights: the middleware account must
        belong to ``group_app_message_middleware`` (read on app notifications
        and on ``qs2.app.message`` documents).
        """
        domain = [
            ("notification_type", "=", "app"),
            ("notification_status", "in", ("ready", "process", "pending")),
        ]
        notifications = self.search(domain, limit=limit, order="id")
        result = []
        for notif in notifications:
            message = notif.mail_message_id
            partner = notif.res_partner_id
            user = partner.user_ids[:1]
            result.append({
                "notification_id": notif.id,
                "message_id": message.id,
                "partner_id": partner.id,
                "partner_name": partner.display_name,
                "user_id": user.id if user else False,
                "login": user.login if user else False,
                "subject": message.subject,
                "body": message.body,
                "author": message.author_id.display_name,
                "date": fields.Datetime.to_string(message.date),
            })
        return result

    def app_mark_sent(self):
        """RPC helper: mark the selected app notifications as delivered ('sent')."""
        app_notifs = self.filtered(lambda n: n.notification_type == "app")
        app_notifs.write({"notification_status": "sent"})
        return True
