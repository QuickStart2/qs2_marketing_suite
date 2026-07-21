{
    "name": "CRM Portal",
    "summary": "Area riservata per referenti portale: consultano e aggiornano i propri lead",
    "description": """
        Espone il CRM a utenti portale con funzionalità ridotta.

        Ogni lead può avere un "Referente portale" (utente portale). Quel
        referente, dalla sua area riservata /my, vede SOLO i lead a lui
        assegnati, in una pipeline per fase con contatori, e può aggiornare
        i soli dati di contatto (nome, email, telefono, indirizzo, iniziativa).

        Non crea né cancella lead. La fase e i dati commerciali
        (valore atteso, probabilità, venditore) sono in sola lettura o nascosti.

        Sicurezza a due livelli:
        - record rule: il portale vede solo i lead con qs2_portal_user_id = sé stesso;
        - field access (_has_field_access): read/write limitati a una whitelist di
          campi anche via RPC diretto, non solo dal controller.
    """,
    "version": "19.0.1.1.0",
    "category": "Marketing",
    "author": "QuickStart2, Leonardo Guerra",
    "website": "https://www.quickstart2.com",
    "license": "AGPL-3",
    "depends": [
        "crm",
        "portal",
        "qs2_marketing_suite_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/crm_lead_portal_rules.xml",
        "views/crm_lead_views.xml",
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "qs2_crm_portal/static/src/scss/portal_leads.scss",
            "qs2_crm_portal/static/src/interactions/leads_kanban.js",
        ],
    },
    "installable": True,
}
