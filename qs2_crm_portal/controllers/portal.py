"""Controller dell'area riservata dei referenti portale.

Route:
- /my                      : card con contatore dei lead
- /my/leads                : pipeline per fase + KPI
- /my/leads/<id>           : dettaglio + form di aggiornamento
- /my/leads/<id>/save      : salvataggio (POST)

Sicurezza: la record rule `crm_lead_rule_portal` limita le righe visibili al
referente; `crm.lead._has_field_access` limita i campi leggibili/scrivibili.
Il controller resta perimetro-agnostico e non usa mai sudo per leggere o
scrivere i dati del portale.
"""

import re

from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CrmLeadPortal(CustomerPortal):

    # ------------------------------------------------------------------
    # Home: card + contatore
    # ------------------------------------------------------------------
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "lead_count" in counters:
            Lead = request.env["crm.lead"]
            values["lead_count"] = (
                Lead.search_count(self._portal_lead_domain())
                if Lead.has_access("read")
                else 0
            )
        return values

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _portal_lead_domain(self):
        """Perimetro: i lead di cui l'utente corrente è referente portale.
        Ridondante con la record rule (difesa in profondità)."""
        return [("qs2_portal_user_id", "=", request.env.user.id)]

    def _get_portal_lead(self, lead_id):
        """Recupera un lead verificando l'accesso in lettura (rispetta la rule)."""
        lead = request.env["crm.lead"].browse(lead_id)
        if not lead.exists():
            raise MissingError(_("Questo lead non esiste o non è più disponibile."))
        lead.check_access("read")
        return lead

    def _lead_form_values(self, lead, overrides=None):
        """Valori correnti dei campi editabili (con eventuali override dal POST)."""
        overrides = overrides or {}
        writable = request.env["crm.lead"]._portal_accessible_fields()[1]
        values = {}
        for fname in writable:
            if fname in overrides:
                values[fname] = overrides[fname]
                continue
            field = lead._fields[fname]
            if field.type == "many2one":
                values[fname] = lead[fname].id
            else:
                values[fname] = lead[fname] or ""
        return values

    def _parse_lead_form(self, post):
        """Estrae dal POST SOLO i campi whitelisted, tipizzati. Anti mass-assignment."""
        Lead = request.env["crm.lead"]
        writable = Lead._portal_accessible_fields()[1]
        vals = {}
        for key in writable:
            if key not in post:
                continue
            raw = post.get(key)
            field = Lead._fields[key]
            if field.type == "many2one":
                vals[key] = int(raw) if raw and str(raw).isdigit() else False
            else:
                vals[key] = (raw or "").strip()
        return vals

    def _validate_lead_form(self, vals):
        """Ritorna (errori, campi_invalidi). Validazione minima lato server."""
        errors = []
        invalid = []
        email = vals.get("email_from")
        if email and not EMAIL_RE.match(email):
            errors.append(_("L'indirizzo email non è valido."))
            invalid.append("email_from")
        # I target m2o devono esistere (evita write error / id arbitrari)
        for fname, model in (("state_id", "res.country.state"), ("country_id", "res.country")):
            fid = vals.get(fname)
            if fid and not request.env[model].sudo().browse(fid).exists():
                errors.append(_("Valore non valido per il campo %s.") % fname)
                invalid.append(fname)
        return errors, invalid

    def _lead_render_values(self, lead, country_id=None, **kw):
        """Valori comuni per dettaglio e form (paesi/province per i select).

        `country_id` filtra l'elenco province: di default il paese salvato sul
        lead, ma nel re-render dopo errore viene passato il paese POSTATO così
        i due select restano coerenti.
        """
        Country = request.env["res.country"].sudo()
        State = request.env["res.country.state"].sudo()
        country_id = lead.country_id.id if country_id is None else country_id
        values = {
            "lead": lead,
            "page_name": "lead",
            "countries": Country.search([]),
            "states": State.search([("country_id", "=", country_id)] if country_id else []),
        }
        values.update(kw)
        return values

    def _normalize_state_country(self, vals, lead):
        """Scarta la provincia se non appartiene al paese (postato o salvato):
        evita di persistere una provincia di un altro paese quando l'utente
        cambia il paese senza aggiornare la provincia."""
        if not vals.get("state_id"):
            return
        country_id = vals.get("country_id") if "country_id" in vals else lead.country_id.id
        state = request.env["res.country.state"].sudo().browse(vals["state_id"])
        if not state.exists() or state.country_id.id != (country_id or False):
            vals["state_id"] = False

    # ------------------------------------------------------------------
    # Pipeline (lista)
    # ------------------------------------------------------------------
    @http.route(["/my/leads"], type="http", auth="user", website=True)
    def portal_my_leads(self, **kw):
        Lead = request.env["crm.lead"]
        if not Lead.has_access("read"):
            return request.redirect("/my")

        domain = self._portal_lead_domain()
        leads = Lead.search(domain, order="stage_id, priority desc, create_date desc")

        # Salva la history per il prev/next del dettaglio (allineata al set reso)
        request.session["my_leads_history"] = leads.ids

        # Raggruppamento per fase (colonne pipeline), in ordine di fase
        columns = []
        seen = {}
        for lead in leads:
            stage = lead.stage_id
            if stage.id not in seen:
                seen[stage.id] = {"stage": stage, "leads": request.env["crm.lead"]}
                columns.append(seen[stage.id])
            seen[stage.id]["leads"] |= lead

        values = {
            "page_name": "lead",
            "columns": columns,
            "lead_total": len(leads),
        }
        return request.render("qs2_crm_portal.portal_my_leads", values)

    # ------------------------------------------------------------------
    # Dettaglio + form
    # ------------------------------------------------------------------
    @http.route(["/my/leads/<int:lead_id>"], type="http", auth="user", website=True)
    def portal_my_lead(self, lead_id, message=None, **kw):
        try:
            lead = self._get_portal_lead(lead_id)
        except (AccessError, MissingError):
            return request.redirect("/my/leads")

        history = request.session.get("my_leads_history", [])
        prev_id = next_id = None
        if lead_id in history:
            idx = history.index(lead_id)
            if idx > 0:
                prev_id = history[idx - 1]
            if idx < len(history) - 1:
                next_id = history[idx + 1]

        values = self._lead_render_values(
            lead,
            form_values=self._lead_form_values(lead),
            errors=[],
            invalid_fields=[],
            message=message,
            prev_id=prev_id,
            next_id=next_id,
        )
        return request.render("qs2_crm_portal.portal_my_lead", values)

    @http.route(["/my/leads/<int:lead_id>/save"], type="http", auth="user", methods=["POST"], website=True)
    def portal_my_lead_save(self, lead_id, **post):
        try:
            lead = self._get_portal_lead(lead_id)
        except (AccessError, MissingError):
            return request.redirect("/my/leads")

        vals = self._parse_lead_form(post)
        self._normalize_state_country(vals, lead)
        errors, invalid = self._validate_lead_form(vals)

        if errors:
            values = self._lead_render_values(
                lead,
                country_id=vals.get("country_id", lead.country_id.id),
                form_values=self._lead_form_values(lead, overrides=vals),
                errors=errors,
                invalid_fields=invalid,
                message=None,
                prev_id=None,
                next_id=None,
            )
            return request.render("qs2_crm_portal.portal_my_lead", values)

        # Backstop anti mass-assignment: solo i campi whitelisted (ridondante con
        # _parse_lead_form, ma protegge da una futura regressione di quel metodo).
        writable = request.env["crm.lead"]._portal_accessible_fields()[1]
        vals = {k: v for k, v in vals.items() if k in writable}

        # Accesso in lettura già verificato (_get_portal_lead → check_access): il
        # lead è del referente. La write è in sudo su un dict SOLO whitelisted
        # (pattern sale.order): serve perché il ricalcolo dei campi di contatto
        # legge partner_id, che il portale non può leggere. Il flag
        # qs2_portal_no_partner_sync impedisce che email/telefono si propaghino
        # su res.partner tramite gli inverse (scrittura fuori perimetro).
        lead.sudo().with_context(qs2_portal_no_partner_sync=True).write(vals)
        return request.redirect("/my/leads/%s?message=updated" % lead.id)
