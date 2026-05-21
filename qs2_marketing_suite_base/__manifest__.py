{
    "name": "Marketing Suite Base",
    "summary": "Piano Media con metriche marketing: CPL, CPC, ROAS e funnel completo",
    "description": """
        Modulo base per la gestione marketing:
        - Brand: anagrafica brand con logo
        - Piano Media: campagna + origine + brand con budget e metriche
        - Metriche automatiche: CPL, CPC, CTR, CPA, ROAS, CPM
        - Funnel completo: Impression → Click → Lead → Conversione → Revenue
    """,
    "version": "19.0.1.0.0",
    "category": "Marketing",
    "author": "QuickStart2, Leonardo Guerra",
    "license": "AGPL-3",
    "depends": ["base", "utm", "crm", "sales_team"],
    "data": [
        "security/ir.model.access.csv",
        "views/qs2_brand_views.xml",
        "views/qs2_agency_views.xml",
        "views/qs2_media_plan_views.xml",
        "views/qs2_ad_views.xml",
        "views/crm_lead_views.xml",
        "views/qs2_rating_criterion_views.xml",
        "views/menu.xml",
        "data/qs2_rating_criterion_seed.xml",
    ],
    "installable": True,
    "application": True,
}
