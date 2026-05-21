from odoo import http
from odoo.http import request


class LeadWebhookHR(http.Controller):

    @http.route("/crm_hr_form/", auth="public", methods=["POST"], csrf=False)
    def crm_hr_form(self, **post):

        name = post.get("nome_e_cognome")
        citta = post.get("citta")
        domanda1 = post.get("domanda1")
        domanda2 = post.get("domanda2")
        domanda3 = post.get("domanda3")
        domanda4 = post.get("domanda4")
        domanda5 = post.get("domanda5")
        domanda6 = post.get("domanda6")
        cellulare = post.get("cellulare")
        email_from = post.get("email")
        utm_medium = post.get("utm_medium")
        utm_campaign = post.get("utm_campaign")
        utm_content = post.get("utm_content")
        utm_source = post.get("utm_source")
        utm_term = post.get("utm_term")
        job_id = post.get("job_id")
        nome_candidatura = post.get("nome_candidatura")

        description = ""
        for field in post.keys():
            description += field + ": " + post[field] + "\n<br>"

        if not name:
            return "Error"

        # UTM Source
        source_id = self._get_or_create("utm.source", "name", utm_source)

        # UTM Medium
        medium_id = self._get_or_create("utm.medium", "name", utm_medium)

        # UTM Campaign
        campaign_id = self._get_or_create("utm.campaign", "name", utm_campaign)

        # Adset
        term_id = self._get_or_create("x_adset", "x_name", utm_term)

        # Creazione candidatura
        applicant = request.env["hr.applicant"].sudo().create({
            "job_id": job_id,
            "partner_name": name,
            "name": nome_candidatura,
            "x_studio_provincia_t": citta,
            "email_from": email_from,
            "x_studio_dati_tecnici": description,
            "x_studio_source_id": source_id,
            "x_studio_mezzo_utm": medium_id,
            "campaign_id": campaign_id,
            "x_studio_utm_content": utm_content,
            "x_studio_term_id": term_id,
            "partner_mobile": cellulare,
            "description": "",
            "stage_id": 1,
            "x_studio_hai_esperienza_pregressa_in_ruoli_simili_1": domanda1,
            "x_studio_quanto_sei_a_tuo_agio_nel_parlare_con_i_clienti": domanda2,
            "x_studio_paziente_e_cordiale_con_i_clienti": domanda3,
            "x_studio_capacit_di_ascolto": domanda4,
            "x_studio_lingua_italiana": domanda5,
            "x_studio_cliente_desidera_parlarne_con_il_partner": domanda6,
        })

        return "OK " + str(applicant.id)

    def _get_or_create(self, model, field, value):
        if not value:
            return 0
        rec = request.env[model].sudo().search([(field, "=", value)], limit=1)
        if rec:
            return rec.id
        rec = request.env[model].sudo().create({field: value})
        return rec.id
