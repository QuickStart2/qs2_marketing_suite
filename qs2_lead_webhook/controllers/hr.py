import logging

from markupsafe import Markup

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LeadWebhookHR(http.Controller):

    @http.route("/crm_hr_form/", auth="public", methods=["POST"], csrf=False)
    def crm_hr_form(self, **post):

        name = post.get("nome_e_cognome")
        citta = post.get("citta")
        cellulare = post.get("cellulare")
        email_from = post.get("email")
        utm_medium = post.get("utm_medium")
        utm_campaign = post.get("utm_campaign")
        utm_source = post.get("utm_source")
        job_id = post.get("job_id")
        nome_candidatura = post.get("nome_candidatura")

        if not name:
            return "Error"

        # job_id arriva come stringa dal POST: va convertito o il Many2one lo
        # scarta silenziosamente (nessuna eccezione, candidatura senza posizione).
        try:
            job_id = int(job_id)
        except (TypeError, ValueError):
            job_id = False

        # Origine: campi standard di utm.mixin (ereditato da hr.applicant).
        source_id = self._get_or_create("utm.source", "name", utm_source)
        medium_id = self._get_or_create("utm.medium", "name", utm_medium)
        campaign_id = self._get_or_create("utm.campaign", "name", utm_campaign)

        # Tutti gli altri dati del form (città, risposte di screening, campi
        # extra) finiscono nelle note della candidatura: niente più campi Studio.
        applicant = request.env["hr.applicant"].sudo().create({
            "job_id": job_id,
            # Nome del candidato mostrato in Selezione del Personale.
            "partner_name": nome_candidatura or name,
            "email_from": email_from,
            "partner_phone": cellulare,
            "source_id": source_id or False,
            "medium_id": medium_id or False,
            "campaign_id": campaign_id or False,
            "applicant_notes": self._build_notes(post, citta),
        })

        return "OK " + str(applicant.id)

    def _build_notes(self, post, citta):
        """Note candidatura (HTML) con città e tutti i dati ricevuti dal form."""
        lines = []
        if citta:
            lines.append(Markup("<b>Città:</b> %s") % citta)
        for key, value in post.items():
            if value:
                lines.append(Markup("<b>%s:</b> %s") % (key, value))
        if not lines:
            return False
        return Markup("<br/>").join(lines)

    def _get_or_create(self, model, field, value):
        if not value or model not in request.env:
            return 0
        rec = request.env[model].sudo().search([(field, "=", value)], limit=1)
        if rec:
            return rec.id
        rec = request.env[model].sudo().create({field: value})
        return rec.id
