import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class Qs2TrackingController(http.Controller):

    @http.route("/qs2/activate", type="json", auth="public", csrf=False)
    def activate_tracking(self, tracking_code=None, url=None):
        """Attiva tracking: salva il codice in sessione e logga la prima visita."""
        if not tracking_code:
            return {"status": "error", "message": "No tracking code"}

        partner = request.env["res.partner"].sudo().search(
            [("qs2_tracking_code", "=", tracking_code.upper())], limit=1,
        )
        if not partner:
            return {"status": "error", "message": "Invalid tracking code"}

        request.session["qs2_tracking_code"] = tracking_code.upper()
        self._log_pageview(partner, url)
        _logger.info(
            "Tracking %s attivato per partner %s", tracking_code, partner.id
        )
        return {"status": "ok", "tracking_code": tracking_code.upper()}

    @http.route("/qs2/pageview", type="json", auth="public", csrf=False)
    def log_pageview(self, url=None, **kwargs):
        """Log pageview per sessioni già tracciate."""
        tracking_code = request.session.get("qs2_tracking_code")
        if not tracking_code:
            return {"status": "no_tracking"}

        partner = request.env["res.partner"].sudo().search(
            [("qs2_tracking_code", "=", tracking_code)], limit=1,
        )
        if not partner:
            return {"status": "not_found"}

        self._log_pageview(partner, url or request.httprequest.referrer)
        return {"status": "ok", "tracking_code": tracking_code}

    def _log_pageview(self, partner, url):
        try:
            httpreq = request.httprequest
            ip = (
                httpreq.environ.get("HTTP_X_REAL_IP")
                or httpreq.environ.get("HTTP_X_FORWARDED_FOR")
                or httpreq.remote_addr
            )
            if ip and "," in ip:
                ip = ip.split(",")[0].strip()

            request.env["qs2.visit"].sudo().create({
                "partner_id": partner.id,
                "url": url or "/",
                "ip_address": ip,
                "user_agent": httpreq.user_agent.string,
                "referer": httpreq.referrer,
                "session_id": request.session.sid,
            })
        except Exception as e:
            _logger.error("Errore log pageview: %s", e)
