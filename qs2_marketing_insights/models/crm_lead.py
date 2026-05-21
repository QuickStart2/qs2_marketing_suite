"""Aggregatore eventi per la timeline lead.

Restituisce una lista di eventi normalizzati provenienti da modelli diversi
(crm.lead, mail.message, qs2.visit, whatsapp.message, sale.order, ...) ordinati
per timestamp. Il frontend OWL ([static/src/timeline/timeline.js]) consuma
questa lista come fonte unica.
"""

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Categorie usate per il color coding lato frontend.
GROUP_MARKETING = "marketing"
GROUP_TRACKING = "tracking"
GROUP_COMM = "comm"
GROUP_SALES = "sales"
GROUP_BILLING = "billing"
GROUP_CRM = "crm"


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.model
    def get_timeline_events(self, lead_id):
        """Punto d'ingresso unico chiamato dall'OWL widget.

        Ritorna lista di dict con campi:
          ts          ISO timestamp
          kind        identificatore corto del tipo evento
          group       categoria (per color coding)
          title       breve descrizione visibile
          subtitle    riga secondaria
          icon        classe FontAwesome (es. 'fa-bullhorn')
          body_html   opzionale, mostrato espandendo l'evento
          link        opzionale, {res_model, res_id} per aprire la scheda
        """
        lead = self.browse(int(lead_id)).exists()
        if not lead:
            return []

        events = []
        events.extend(lead._timeline_origin())
        events.extend(lead._timeline_ad())
        events.extend(lead._timeline_stage_changes())
        events.extend(lead._timeline_visits())
        events.extend(lead._timeline_milestones())
        events.extend(lead._timeline_whatsapp())
        events.extend(lead._timeline_chatter())
        events.extend(lead._timeline_activities())
        events.extend(lead._timeline_sales())
        events.extend(lead._timeline_invoices())
        events.extend(lead._timeline_outcome())

        # Ordina cronologicamente. Eventi senza timestamp vanno in fondo.
        events.sort(key=lambda e: e.get("ts") or "9999")
        return events

    # ------------------------------------------------------------------
    # Origine — sempre primo evento
    # ------------------------------------------------------------------
    def _timeline_origin(self):
        self.ensure_one()
        bits = []
        if self.source_id:
            bits.append(self.source_id.name)
        if self.medium_id:
            bits.append(self.medium_id.name)
        if self.campaign_id:
            bits.append(self.campaign_id.name)
        if self.qs2_initiative:
            bits.append(self.qs2_initiative)
        subtitle = " · ".join(bits) or "(origine non rilevata)"

        body_parts = []
        if self.email_from:
            body_parts.append(f"<div><b>Email:</b> {self.email_from}</div>")
        if self.phone:
            body_parts.append(f"<div><b>Telefono:</b> {self.phone}</div>")
        if self.partner_name:
            body_parts.append(f"<div><b>Azienda:</b> {self.partner_name}</div>")
        if self.country_id:
            geo = self.country_id.name
            if self.state_id:
                geo = f"{self.state_id.name}, {geo}"
            if self.city:
                geo = f"{self.city} ({geo})"
            body_parts.append(f"<div><b>Provenienza:</b> {geo}</div>")

        return [{
            "id": f"origin-{self.id}",
            "ts": _iso(self.create_date),
            "kind": "origin",
            "group": GROUP_MARKETING,
            "title": "Lead acquisito",
            "subtitle": subtitle,
            "icon": "fa-flag-checkered",
            "body_html": "".join(body_parts) or False,
            "link": False,
        }]

    # ------------------------------------------------------------------
    # Inserzione vista (qs2.ad)
    # ------------------------------------------------------------------
    def _timeline_ad(self):
        self.ensure_one()
        if not self.qs2_ad_id:
            return []
        ad = self.qs2_ad_id
        mp = ad.media_plan_id
        cost = mp.cost if mp else 0
        brand = (self.qs2_brand_id.name or "") if self.qs2_brand_id else ""
        subtitle_bits = [ad.platform.title()] if ad.platform else []
        if brand:
            subtitle_bits.append(brand)
        if mp:
            subtitle_bits.append(f"Piano {mp.month}/{mp.year}")
        body = ""
        if ad.platform_ref:
            body += f"<div><b>Ref piattaforma:</b> {ad.platform_ref}</div>"
        if cost:
            body += f"<div><b>Budget piano media:</b> € {cost:,.0f}</div>"
        if mp and mp.cpl:
            body += f"<div><b>CPL piano media:</b> € {mp.cpl:,.2f}</div>"

        return [{
            "id": f"ad-{ad.id}",
            "ts": _iso(self.create_date),
            "kind": "ad",
            "group": GROUP_MARKETING,
            "title": f"Cliccata inserzione: {ad.name}",
            "subtitle": " · ".join(subtitle_bits) or False,
            "icon": "fa-bullhorn",
            "body_html": body or False,
            "link": {"res_model": "qs2.ad", "res_id": ad.id},
        }]

    # ------------------------------------------------------------------
    # Cambi di fase CRM — leggiamo da mail.tracking.value
    # ------------------------------------------------------------------
    def _timeline_stage_changes(self):
        self.ensure_one()
        Tracking = self.env["mail.tracking.value"]
        field = self.env["ir.model.fields"]._get("crm.lead", "stage_id")
        if not field:
            return []
        trackings = Tracking.sudo().search([
            ("field_id", "=", field.id),
            ("mail_message_id.model", "=", "crm.lead"),
            ("mail_message_id.res_id", "=", self.id),
        ])
        events = []
        for t in trackings:
            new_name = _stage_name(self, t.new_value_integer)
            old_name = _stage_name(self, t.old_value_integer)
            events.append({
                "id": f"stage-{t.id}",
                "ts": _iso(t.mail_message_id.date),
                "kind": "stage",
                "group": GROUP_CRM,
                "title": f"Fase: {old_name or '—'} → {new_name or '—'}",
                "subtitle": False,
                "icon": "fa-arrow-circle-right",
                "body_html": False,
                "link": False,
            })
        return events

    # ------------------------------------------------------------------
    # Visite web (qs2.visit)
    # ------------------------------------------------------------------
    def _timeline_visits(self):
        self.ensure_one()
        if not self.partner_id:
            return []
        visits = self.env["qs2.visit"].sudo().search([
            ("partner_id", "=", self.partner_id.id),
        ], order="timestamp asc")
        events = []
        for v in visits:
            events.append({
                "id": f"visit-{v.id}",
                "ts": _iso(v.timestamp),
                "kind": "visit",
                "group": GROUP_TRACKING,
                "title": "Visita web",
                "subtitle": v.url or False,
                "icon": "fa-eye",
                "body_html": (
                    f"<div><b>IP:</b> {v.ip_address or '—'}</div>"
                    f"<div><b>Referer:</b> {v.referer or '—'}</div>"
                ),
                "link": False,
            })
        return events

    # ------------------------------------------------------------------
    # Milestone raggiunte — usiamo il timestamp della PRIMA visita che
    # matcha la regola della milestone.
    # ------------------------------------------------------------------
    def _timeline_milestones(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner or not partner.qs2_milestone_ids:
            return []
        Visit = self.env["qs2.visit"].sudo()
        events = []
        for milestone in partner.qs2_milestone_ids:
            rules = self.env["qs2.tracking.rule"].sudo().search([
                ("milestone_id", "=", milestone.id),
            ])
            first_ts = False
            for visit in Visit.search([("partner_id", "=", partner.id)], order="timestamp asc"):
                if any(r.matches(visit.url) for r in rules):
                    first_ts = visit.timestamp
                    break
            events.append({
                "id": f"milestone-{milestone.id}",
                "ts": _iso(first_ts),
                "kind": "milestone",
                "group": GROUP_TRACKING,
                "title": f"Milestone: {milestone.name}",
                "subtitle": milestone.description or False,
                "icon": "fa-trophy",
                "body_html": False,
                "link": {"res_model": "qs2.tracking.milestone", "res_id": milestone.id},
            })
        return events

    # ------------------------------------------------------------------
    # Messaggi WhatsApp del partner del lead
    # ------------------------------------------------------------------
    def _timeline_whatsapp(self):
        self.ensure_one()
        Conv = self.env["whatsapp.conversation"].sudo()
        domain = []
        if self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))
        elif self.phone:
            domain.append(("phone", "=", self.phone))
        else:
            return []
        conv = Conv.search(domain, limit=1)
        if not conv:
            return []
        events = []
        for msg in conv.message_ids:
            direction = "Inviato" if msg.direction == "out" else "Ricevuto"
            events.append({
                "id": f"wa-{msg.id}",
                "ts": _iso(msg.timestamp),
                "kind": f"whatsapp-{msg.direction}",
                "group": GROUP_COMM,
                "title": f"WhatsApp {direction}",
                "subtitle": (msg.body or "")[:120],
                "icon": "fa-whatsapp",
                "body_html": False,
                "link": {"res_model": "whatsapp.conversation", "res_id": conv.id},
            })
        return events

    # ------------------------------------------------------------------
    # Mail.message (note, email, log) del lead
    # ------------------------------------------------------------------
    def _timeline_chatter(self):
        self.ensure_one()
        Message = self.env["mail.message"].sudo()
        msgs = Message.search([
            ("model", "=", "crm.lead"),
            ("res_id", "=", self.id),
            ("message_type", "in", ("email", "comment")),
        ], order="date asc")
        events = []
        for m in msgs:
            mtype = m.message_type
            if mtype == "email":
                title = "Email"
                icon = "fa-envelope"
            else:
                title = "Nota interna" if (m.subtype_id and m.subtype_id.internal) else "Messaggio"
                icon = "fa-sticky-note"
            subject = m.subject or ""
            body = m.body or ""
            events.append({
                "id": f"msg-{m.id}",
                "ts": _iso(m.date),
                "kind": "mail",
                "group": GROUP_COMM,
                "title": title,
                "subtitle": subject or (m.author_id.name if m.author_id else "")[:120],
                "icon": icon,
                "body_html": body[:600] if body else False,
                "link": False,
            })
        return events

    # ------------------------------------------------------------------
    # Activity (mail.activity) — pianificate e completate
    # ------------------------------------------------------------------
    def _timeline_activities(self):
        self.ensure_one()
        Activity = self.env["mail.activity"].sudo()
        # Pianificate ancora aperte
        plan = Activity.search([
            ("res_model", "=", "crm.lead"),
            ("res_id", "=", self.id),
        ])
        events = []
        for a in plan:
            events.append({
                "id": f"act-plan-{a.id}",
                "ts": _iso(a.date_deadline) + "T00:00:00" if a.date_deadline else False,
                "kind": "activity",
                "group": GROUP_CRM,
                "title": f"Pianificato: {a.summary or a.activity_type_id.name or '—'}",
                "subtitle": (a.user_id.name or "") if a.user_id else False,
                "icon": "fa-clock-o",
                "body_html": a.note or False,
                "link": False,
            })
        return events

    # ------------------------------------------------------------------
    # Sale order (preventivi + confermati)
    # ------------------------------------------------------------------
    def _timeline_sales(self):
        self.ensure_one()
        if "sale.order" not in self.env:
            return []
        SO = self.env["sale.order"].sudo()
        orders = SO.search([("opportunity_id", "=", self.id)], order="date_order asc")
        events = []
        for so in orders:
            is_quote = so.state in ("draft", "sent")
            title = ("Preventivo " if is_quote else "Vendita ") + so.name
            icon = "fa-file-text-o" if is_quote else "fa-shopping-cart"
            events.append({
                "id": f"so-{so.id}",
                "ts": _iso(so.date_order),
                "kind": "quote" if is_quote else "sale",
                "group": GROUP_SALES,
                "title": title,
                "subtitle": f"€ {so.amount_total:,.0f} · {so.state}",
                "icon": icon,
                "body_html": False,
                "link": {"res_model": "sale.order", "res_id": so.id},
            })
        return events

    # ------------------------------------------------------------------
    # Fatture associate (account.move via sale_order.invoice_ids)
    # ------------------------------------------------------------------
    def _timeline_invoices(self):
        self.ensure_one()
        if "sale.order" not in self.env or "account.move" not in self.env:
            return []
        SO = self.env["sale.order"].sudo()
        orders = SO.search([("opportunity_id", "=", self.id)])
        events = []
        seen = set()
        for so in orders:
            for inv in so.invoice_ids:
                if inv.id in seen or inv.move_type not in ("out_invoice", "out_refund"):
                    continue
                seen.add(inv.id)
                events.append({
                    "id": f"inv-{inv.id}",
                    "ts": _iso(inv.invoice_date or inv.date),
                    "kind": "invoice",
                    "group": GROUP_BILLING,
                    "title": f"Fattura {inv.name or inv.id}",
                    "subtitle": f"€ {inv.amount_total:,.0f} · {inv.payment_state or inv.state}",
                    "icon": "fa-money",
                    "body_html": False,
                    "link": {"res_model": "account.move", "res_id": inv.id},
                })
        return events

    # ------------------------------------------------------------------
    # Esito finale (won/lost)
    # ------------------------------------------------------------------
    def _timeline_outcome(self):
        self.ensure_one()
        if self.won_status == "won":
            return [{
                "id": f"outcome-{self.id}",
                "ts": _iso(self.date_closed),
                "kind": "won",
                "group": GROUP_SALES,
                "title": "Vinto",
                "subtitle": f"Ricavo atteso € {self.expected_revenue:,.0f}",
                "icon": "fa-check-circle",
                "body_html": False,
                "link": False,
            }]
        if self.won_status == "lost":
            return [{
                "id": f"outcome-{self.id}",
                "ts": _iso(self.date_closed),
                "kind": "lost",
                "group": GROUP_SALES,
                "title": "Perso",
                "subtitle": (self.lost_reason_id.name if self.lost_reason_id else False),
                "icon": "fa-times-circle",
                "body_html": False,
                "link": False,
            }]
        return []


def _iso(dt):
    """Datetime/date → ISO string, None-safe."""
    if not dt:
        return False
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _stage_name(lead, stage_id):
    if not stage_id:
        return None
    stage = lead.env["crm.stage"].browse(stage_id).exists()
    return stage.name if stage else None
