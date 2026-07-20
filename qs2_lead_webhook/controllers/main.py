"""Controller HTTP per i webhook di acquisizione lead.

Espone due endpoint POST:
- /crm_lead_form/  : creazione lead da landing page o form esterno
- /crm_update_chatbot/ : tagging lead esistente da chatbot

I lead vengono creati su `crm.lead` usando esclusivamente i campi standard
Odoo + i campi aggiunti da `qs2_marketing_suite_base` (qs2_ad_id, qs2_brand_id,
qs2_agency_id, qs2_initiative). Nessun campo `x_studio_*` legacy.
L'assegnazione a venditore/team passa dal motore di regole
`qs2.lead.routing.rule` (con fallback a ir.config_parameter).
"""

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class LeadWebhookMain(http.Controller):

    @http.route("/crm_lead_form/", auth="public", methods=["POST"], csrf=False)
    def crm_lead_form(self, **post):
        # Dati anagrafici
        name = post.get("nome_e_cognome") or post.get("name")
        email = post.get("email")
        phone = post.get("cellulare") or post.get("phone")
        city = post.get("citta") or post.get("city")
        street = post.get("street")
        provincia = post.get("provincia") or post.get("state")
        cap = (post.get("cap") or post.get("zip") or "").strip() or False
        paese = post.get("paese") or post.get("country") or post.get("country_code")
        lingua = post.get("lingua") or post.get("lang")

        # UTM / origine
        utm_source = post.get("utm_source")
        utm_medium = post.get("utm_medium")
        utm_campaign = post.get("utm_campaign")
        iniziativa = post.get("iniziativa") or post.get("utm_term")
        agenzia = post.get("agenzia")
        brand = post.get("brand")
        ad_ref = post.get("ad_ref")  # riferimento inserzione su piattaforma

        # Antispam: lista di email bloccate via ir.config_parameter
        # (CSV oppure singola email). Esempio:
        #   key=qs2_lead_webhook.email_blocklist  value="abc@x.com,def@y.com"
        blocklist = self._get_email_blocklist()
        if email and email.lower().strip() in blocklist:
            return "OK BLOCKED"

        if not name:
            return "Error"

        # Provincia (Italia), paese e lingua — servono al routing e al lead
        provincia_id = self._lookup_province(provincia)
        country_id = self._lookup_country(paese, provincia_id)
        lang_rec = self._lookup_lang(lingua)
        lang_code = lang_rec.code if lang_rec else False

        # UTM
        source_id = self._get_or_create_record("utm.source", "name", utm_source)
        medium_id = self._get_or_create_record("utm.medium", "name", utm_medium)
        campaign_id = self._get_or_create_record("utm.campaign", "name", utm_campaign)

        # Brand / Agenzia (qs2.brand, qs2.agency)
        brand_id = self._get_or_create_record("qs2.brand", "name", brand)
        agency_id = self._get_or_create_record("qs2.agency", "name", agenzia)

        # Inserzione: lookup-only su qs2.ad.platform_ref
        qs2_ad_id = False
        if ad_ref:
            ad = request.env["qs2.ad"].sudo().search(
                [("platform_ref", "=", ad_ref)], limit=1,
            )
            if ad:
                qs2_ad_id = ad.id

        # Descrizione: serializzazione di tutti i campi extra ricevuti.
        # Utile per debug / dati custom non mappati nello schema qs2.
        description = "\n".join(f"{k}: {v}" for k, v in post.items() if v)

        # Routing del lead: prima regola che matcha
        # (qs2.lead.routing.rule), poi fallback al parametro globale.
        lead_vals_for_routing = {
            "country_id": country_id or False,
            "state_id": provincia_id,
            "zip": cap,
            "lang": lang_code,
            "source_id": source_id or False,
            "qs2_initiative": iniziativa,
            "qs2_brand_id": brand_id or False,
        }
        routed_user_id, routed_team_id = request.env[
            "qs2.lead.routing.rule"
        ].sudo().route(lead_vals_for_routing)
        if not routed_user_id:
            param = request.env["ir.config_parameter"].sudo().get_param(
                "qs2_lead_webhook.default_user_id"
            )
            routed_user_id = int(param) if param and param.isdigit() else False

        # Build vals — solo None/False skippati così Odoo applica i default
        vals = {
            "name": name,
            "type": "opportunity",
            "email_from": email,
            "phone": phone,
            "city": city,
            "street": street,
            "zip": cap,
            "state_id": provincia_id or False,
            "country_id": country_id or False,
            "lang_id": lang_rec.id or False,
            "source_id": source_id or False,
            "medium_id": medium_id or False,
            "campaign_id": campaign_id or False,
            "description": description,
            "team_id": routed_team_id or False,
            "qs2_initiative": iniziativa,
            "qs2_brand_id": brand_id or False,
            "qs2_agency_id": agency_id or False,
            "qs2_ad_id": qs2_ad_id,
        }
        vals = {k: v for k, v in vals.items() if v not in (None, "", 0)}
        # user_id va passato sempre, anche a False: se la chiave manca, Odoo
        # applica il default di crm.lead (l'utente della sessione, che su una
        # route auth="public" è il Public user). Il lead risulterebbe assegnato
        # e verrebbe escluso dall'assegnazione automatica del team.
        vals["user_id"] = routed_user_id or False
        crm_lead = request.env["crm.lead"].sudo().create(vals)
        return "OK " + str(crm_lead.id)

    # ------------------------------------------------------------------
    # Chatbot update — aggiunge un tag a un lead esistente identificato per
    # numero (con varianti di formato) e opzionalmente nome.
    # ------------------------------------------------------------------
    @http.route("/crm_update_chatbot/", auth="public", methods=["POST"], csrf=False)
    def crm_update_chatbot(self, **post):
        name = post.get("userName")
        phone = post.get("userNumber")

        _logger.info("crm_update_chatbot: %s - %s", name, phone)
        if not name:
            return "Error"

        # Lookup lead per varianti di numero
        leads = None
        for variant in self._build_phone_variations(phone):
            leads = request.env["crm.lead"].sudo().search(
                [("phone", "=", variant), ("name", "=", name)],
                order="create_date desc", limit=1,
            )
            if not leads:
                leads = request.env["crm.lead"].sudo().search(
                    [("phone", "=", variant)],
                    order="create_date desc", limit=1,
                )
            if leads:
                break

        if not leads:
            return "Error - contact not found"

        lead = leads[0]
        chatbot_tag = request.env["ir.config_parameter"].sudo().get_param("CHATBOT_TAG")
        if chatbot_tag and chatbot_tag.isdigit() and int(chatbot_tag) > 0:
            lead.sudo().write({"tag_ids": [(4, int(chatbot_tag))]})
        else:
            body = (
                "Il Chatbot vorrebbe inserire in target questo lead, "
                "ma non c'è nessun tag configurato. "
                "Verifica il parametro CHATBOT_TAG."
            )
            request.env["mail.message"].sudo().create([{
                "model": "crm.lead",
                "res_id": lead.id,
                "message_type": "comment",
                "body": f"ALERT WEBHOOK: {body}",
            }])
        return "OK " + str(lead.id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_or_create_record(self, model, field, value):
        """Cerca un record per `field=value`, se non esiste lo crea.
        Ritorna l'ID (0 se value è falsy o il modello non esiste).
        """
        if not value:
            return 0
        if model not in request.env:
            return 0
        rec = request.env[model].sudo().search([(field, "=", value)], limit=1)
        if rec:
            return rec.id
        rec = request.env[model].sudo().create({field: value})
        return rec.id

    def _lookup_province(self, provincia):
        """Provincia IT: prima per `code` (es. 'MI'), poi per `name`."""
        if not provincia:
            return False
        country = request.env.ref("base.it", raise_if_not_found=False)
        if not country:
            return False
        State = request.env["res.country.state"].sudo()
        st = State.search([
            ("code", "=", provincia),
            ("country_id", "=", country.id),
        ], limit=1)
        if not st:
            st = State.search([
                ("name", "=", provincia),
                ("country_id", "=", country.id),
            ], limit=1)
        return st.id if st else False

    def _lookup_country(self, paese, provincia_id=False):
        """res.country per code ISO2 ('IT') o name esatto.

        Se `paese` è fornito ma non risolve, ritorna False: NON deduce il paese
        dalla provincia (eviterebbe di assegnare silenziosamente un paese
        sbagliato). La deduzione dalla provincia scatta solo se `paese` è vuoto.
        """
        Country = request.env["res.country"].sudo()
        if paese:
            paese = paese.strip()
            # code è size=2: Odoo tronca il valore di ricerca a 2 char, quindi
            # "Francia" matcherebbe "FR". Tento il code solo per input ISO2.
            country = Country.browse()
            if len(paese) == 2:
                country = Country.search([("code", "=", paese.upper())], limit=1)
            if not country:
                # name è traducibile (jsonb): confronto esatto su en_US per
                # determinismo su una route pubblica (il lang del context varia).
                country = Country.with_context(lang="en_US").search(
                    [("name", "=", paese)], limit=1
                )
            if not country:
                _logger.info("crm_lead_form: paese '%s' non risolto", paese)
            return country.id if country else False
        if provincia_id:
            state = request.env["res.country.state"].sudo().browse(provincia_id)
            return state.country_id.id or False
        return False

    def _lookup_lang(self, lingua):
        """res.lang installato che matcha `lingua` (codice 'it_IT' o prefisso 'it').

        Ritorna il recordset res.lang (vuoto se non risolto). Serve un codice
        normalizzato perché il campo `lang` delle regole di routing è una
        Selection su res.lang.get_installed().
        """
        Lang = request.env["res.lang"].sudo()
        if not lingua:
            return Lang.browse()
        lingua = lingua.strip()
        installed = [code for code, _name in Lang.get_installed()]
        match = next((c for c in installed if c.lower() == lingua.lower()), None)
        if not match:
            # match per prefisso: preferisco it_IT quando lingua='it'
            prefix = lingua.lower().split("_")[0]
            candidates = [c for c in installed if c.split("_")[0].lower() == prefix]
            if candidates:
                canonical = f"{prefix}_{prefix.upper()}"
                match = next(
                    (c for c in candidates if c.lower() == canonical.lower()),
                    sorted(candidates)[0],
                )
        if not match:
            return Lang.browse()
        return Lang.search([("code", "=", match)], limit=1)

    def _get_email_blocklist(self):
        """CSV in ir.config_parameter `qs2_lead_webhook.email_blocklist`."""
        raw = request.env["ir.config_parameter"].sudo().get_param(
            "qs2_lead_webhook.email_blocklist", default=""
        )
        return {e.strip().lower() for e in raw.split(",") if e.strip()}

    def _build_phone_variations(self, cellulare):
        """Genera varianti del numero per la lookup robusta nel chatbot."""
        if not cellulare:
            return []
        variations = [cellulare]
        number = "".join(filter(str.isdigit, cellulare))
        if number.startswith("00"):
            number = "+" + number[2:]
        elif not number.startswith("+"):
            number = "+" + number
        if number.startswith("+39") and len(number) >= 13:
            formatted = f"{number[:3]} {number[3:6]} {number[6:9]} {number[9:13]}"
            variations.append(formatted)
        if cellulare.startswith("0039"):
            variations.append("+39" + cellulare[4:])
        if cellulare.startswith("0041"):
            variations.append("+41" + cellulare[4:])
        if cellulare.startswith("+"):
            variations.append("00" + cellulare[1:])
        else:
            variations.append("+39" + cellulare)
        if not cellulare.startswith("0039"):
            variations.append("0039" + cellulare)
        return variations
