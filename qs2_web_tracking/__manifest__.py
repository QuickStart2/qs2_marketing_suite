{
    "name": "Web Tracking",
    "version": "19.0.1.0.0",
    "category": "Marketing",
    "summary": "Codice tracking univoco e tracciamento visite web",
    "description": """
        Modulo per il tracciamento web dei contatti:
        - Codice tracking univoco di 12 caratteri per ogni contatto
        - Tracking visite web con parametro ?track=CODE
        - Normalizzazione automatica numeri di telefono (formato E164)
    """,
    "author": "QuickStart2, Leonardo Guerra",
    "license": "AGPL-3",
    "depends": ["crm", "phone_validation", "website"],
    "data": [
        "security/ir.model.access.csv",
        "views/crm_lead_views.xml",
        "views/qs2_visit_views.xml",
        "views/res_partner_views.xml",
        "views/qs2_tracking_milestone_views.xml",
        "data/qs2_tracking_seed.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "qs2_web_tracking/static/src/js/tracking.js",
        ],
    },
    "installable": True,
    "application": False,
    "post_init_hook": "_backfill_tracking_codes",
}
