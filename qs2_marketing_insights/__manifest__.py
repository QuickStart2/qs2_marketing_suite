{
    "name": "Marketing Insights",
    "summary": "Timeline visiva del lead: origine → visite → vendite → fatturato",
    "description": """
        Aggrega in un'unica timeline gli eventi del lead provenienti da:
        - Origine (UTM, inserzione, brand, agenzia)
        - Visite web e milestone (qs2_web_tracking)
        - Conversazioni WhatsApp (qs2_whatsapp_bridge)
        - Messaggi e note del chatter
        - Cambi di fase CRM
        - Preventivi, ordini di vendita e fatture

        Il widget OWL viene incastonato nel form del lead come tab "Storia".
    """,
    "version": "19.0.1.0.1",
    "category": "Marketing",
    "author": "QuickStart2, Leonardo Guerra",
    "website": "https://www.quickstart2.com",
    "license": "AGPL-3",
    "depends": [
        "crm",
        "mail",
        "sale",
        "qs2_marketing_suite_base",
        "qs2_web_tracking",
        "qs2_whatsapp_bridge",
    ],
    "data": [
        "views/crm_lead_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "qs2_marketing_insights/static/src/timeline/timeline.js",
            "qs2_marketing_insights/static/src/timeline/timeline.xml",
            "qs2_marketing_insights/static/src/timeline/timeline.scss",
        ],
    },
    "installable": True,
    "application": False,
}
