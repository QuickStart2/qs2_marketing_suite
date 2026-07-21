"""Controller dell'area riservata dei referenti portale.

Route:
- /my                          : card con contatore dei lead
- /my/leads                    : pipeline kanban per fase + KPI
- /my/leads/<id>               : dettaglio (statusbar, form contatto, chatter)
- /my/leads/<id>/save          : salvataggio dati di contatto (POST)
- /my/leads/<id>/set_stage     : cambio fase da drag&drop (JSON-RPC)
- /my/leads/<id>/note          : aggiunta di una nota/commento (POST)

Sicurezza: la record rule `crm_lead_rule_portal` limita le righe visibili al
referente; `crm.lead._has_field_access` limita i campi leggibili/scrivibili.
Ogni scrittura verifica prima l'accesso in lettura sul record NON-sudo
(_get_portal_lead → check_access, che fa scattare la rule) e solo dopo scrive
in sudo su valori controllati.
"""

import re

from markupsafe import Markup, escape

from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Palette colori Odoo ($o-colors): indice → hex. Usata per gli header colonna.
ODOO_PALETTE = [
    "#a2a2a2", "#ee2d2d", "#dc8534", "#e8bb1d", "#5794dd", "#9f628f",
    "#db8865", "#41a9a2", "#304be0", "#ee2f8a", "#61c36e", "#9872e6",
]


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

    def _portal_stages(self):
        """Tutte le fasi CRM, in ordine. Lette in sudo (dato non sensibile)."""
        return request.env["crm.stage"].sudo().search([])

    def _portal_lead_messages(self, lead, limit=30):
        """Cronologia visibile al portale: solo commenti pubblici (mt_comment),
        escludendo sia le note interne (mt_note) sia i messaggi marcati
        "Solo dipendenti" (is_internal). Replica il filtro canonico del portale
        (mail.message._get_search_domain_share) perché la lettura è in sudo e
        quindi bypassa l'ACL di mail.message. Search con limite: niente carico
        di tutti i message_ids del lead."""
        mt_comment = request.env.ref("mail.mt_comment")
        return request.env["mail.message"].sudo().search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead.id),
            ("subtype_id", "=", mt_comment.id),
            ("is_internal", "=", False),
        ], order="date desc", limit=limit)

    def _lead_form_values(self, lead, overrides=None):
        """Valori correnti dei campi editabili (con eventuali override dal POST)."""
        overrides = overrides or {}
        writable = request.env["crm.lead"]._portal_accessible_fields()[1]
        values = {}
        for fname in writable:
            if fname == "stage_id":
                continue  # la fase si cambia dalla pipeline, non dal form
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
        """Estrae dal POST SOLO i campi contatto whitelisted. Anti mass-assignment.
        La fase (stage_id) è esclusa: si cambia solo dalla route dedicata."""
        Lead = request.env["crm.lead"]
        writable = Lead._portal_accessible_fields()[1] - {"stage_id"}
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
        for fname, model in (("state_id", "res.country.state"), ("country_id", "res.country")):
            fid = vals.get(fname)
            if fid and not request.env[model].sudo().browse(fid).exists():
                errors.append(_("Valore non valido per il campo %s.") % fname)
                invalid.append(fname)
        return errors, invalid

    def _lead_render_values(self, lead, country_id=None, **kw):
        """Valori comuni per dettaglio e form (fasi, chatter, paesi/province)."""
        Country = request.env["res.country"].sudo()
        State = request.env["res.country.state"].sudo()
        country_id = lead.country_id.id if country_id is None else country_id
        stages = self._portal_stages()
        current_ids = list(stages.ids)
        values = {
            "lead": lead,
            "page_name": "lead",
            "stages": stages,
            # indice della fase corrente nell'elenco ordinato: la statusbar
            # marca "raggiunte" le fasi con indice <= questo (robusto anche con
            # sequenze uguali o lead senza fase → -1, nessuna raggiunta).
            "current_stage_index": current_ids.index(lead.stage_id.id) if lead.stage_id.id in current_ids else -1,
            "messages": self._portal_lead_messages(lead),
            "countries": Country.search([]),
            "states": State.search([("country_id", "=", country_id)]) if country_id else State.browse(),
        }
        values.update(kw)
        return values

    def _normalize_state_country(self, vals, lead):
        """Scarta la provincia se non appartiene al paese (postato o salvato)."""
        if not vals.get("state_id"):
            return
        country_id = vals.get("country_id") if "country_id" in vals else lead.country_id.id
        state = request.env["res.country.state"].sudo().browse(vals["state_id"])
        if not state.exists() or state.country_id.id != (country_id or False):
            vals["state_id"] = False

    # ------------------------------------------------------------------
    # Pipeline kanban
    # ------------------------------------------------------------------
    @http.route(["/my/leads"], type="http", auth="user", website=True)
    def portal_my_leads(self, **kw):
        Lead = request.env["crm.lead"]
        if not Lead.has_access("read"):
            return request.redirect("/my")

        leads = Lead.search(
            self._portal_lead_domain(), order="priority desc, create_date desc"
        )
        request.session["my_leads_history"] = leads.ids

        by_stage = {}
        for lead in leads:
            by_stage.setdefault(lead.stage_id.id, request.env["crm.lead"])
            by_stage[lead.stage_id.id] |= lead

        # Una colonna per OGNI fase (anche vuote → si può trascinare dentro).
        # `% len` difende da crm.stage.color fuori range (evita IndexError → 500).
        columns = []
        for i, stage in enumerate(self._portal_stages()):
            columns.append({
                "stage": stage,
                "leads": by_stage.get(stage.id, request.env["crm.lead"]),
                "color": ODOO_PALETTE[(stage.color or ((i % 11) + 1)) % len(ODOO_PALETTE)],
            })

        won = leads.filtered(lambda l: l.stage_id.is_won)
        values = {
            "page_name": "lead",
            "columns": columns,
            # lead senza fase: mostrati in una colonna dedicata non-droppable,
            # così il totale coincide con le card visibili (niente lead invisibili).
            "no_stage_leads": by_stage.get(False, request.env["crm.lead"]),
            "lead_total": len(leads),
            "lead_won": len(won),
        }
        return request.render("qs2_crm_portal.portal_my_leads", values)

    # ------------------------------------------------------------------
    # Dettaglio
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

        # Backstop anti mass-assignment: solo i campi contatto whitelisted.
        writable = request.env["crm.lead"]._portal_accessible_fields()[1] - {"stage_id"}
        vals = {k: v for k, v in vals.items() if k in writable}

        # Accesso già verificato (rule). Write in sudo su dict whitelisted; il
        # flag evita la propagazione email/telefono su res.partner via inverse.
        lead.sudo().with_context(qs2_portal_no_partner_sync=True).write(vals)
        return request.redirect("/my/leads/%s?message=updated" % lead.id)

    # ------------------------------------------------------------------
    # Cambio fase (drag&drop) — JSON-RPC, esente da CSRF ma auth=user
    # ------------------------------------------------------------------
    @http.route(["/my/leads/<int:lead_id>/set_stage"], type="jsonrpc", auth="user", website=True)
    def portal_lead_set_stage(self, lead_id, stage_id):
        # check_access('read') sul record NON-sudo → la rule garantisce che il
        # lead sia del referente; solleva se non lo è (il JS fa rollback).
        lead = self._get_portal_lead(lead_id)
        stage = request.env["crm.stage"].sudo().browse(int(stage_id))
        if not stage.exists():
            return {"ok": False, "message": _("Fase non valida.")}
        # Portare un lead in una fase "Vinto" è un'azione commerciale con effetti
        # globali (probability=100, date_closed, scoring PLS, automazioni on-won):
        # bloccata per il portale salvo abilitazione esplicita via parametro
        # `qs2_crm_portal.allow_portal_won`.
        if stage.is_won:
            allow = request.env["ir.config_parameter"].sudo().get_param(
                "qs2_crm_portal.allow_portal_won", "False"
            )
            if str(allow).lower() not in ("1", "true", "yes"):
                return {"ok": False, "message": _("Non puoi spostare un lead nella fase Vinto.")}
        lead.sudo().with_context(qs2_portal_no_partner_sync=True).write({"stage_id": stage.id})
        return {"ok": True, "stage_id": stage.id, "stage_name": stage.name}

    # ------------------------------------------------------------------
    # Nota / commento nel chatter
    # ------------------------------------------------------------------
    @http.route(["/my/leads/<int:lead_id>/note"], type="http", auth="user", methods=["POST"], website=True)
    def portal_lead_note(self, lead_id, note_body=None, **post):
        try:
            lead = self._get_portal_lead(lead_id)
        except (AccessError, MissingError):
            return request.redirect("/my/leads")

        body = (note_body or "").strip()[:5000]  # cap difensivo sulla lunghezza
        if body:
            # HTML sicuro: ogni riga escapata, a capo → <br/>. L'autore è
            # env.user.partner_id (message_post, non falsificabile). Commento
            # pubblico (mt_comment) così il referente lo rivede nel chatter.
            safe = Markup("<br/>").join(escape(line) for line in body.split("\n"))
            lead.sudo().message_post(
                body=safe,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        return request.redirect("/my/leads/%s?message=noted#chatter" % lead.id)
