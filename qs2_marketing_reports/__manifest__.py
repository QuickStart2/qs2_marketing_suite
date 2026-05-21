{
    "name": "Marketing Reports",
    "summary": "Report marketing, qualita lead e vendite preconfigurati",
    "description": """
        Report SQL preconfigurati basati su bi_sql_editor:
        - Monitoraggio qualita lead (motivi perdita, lavorabilita)
        - Reportistica marketing (lead, budget, CPL, conversioni per mese)
        - Reportistica vendite (fatturato per venditore)

        All'installazione vengono creati 3 report in stato bozza.
        Per attivarli: aprire ciascun report e cliccare
        Valida SQL > Crea modello > Crea interfaccia.
    """,
    "version": "19.0.1.0.0",
    "category": "Marketing",
    "author": "QuickStart2, Leonardo Guerra",
    "license": "AGPL-3",
    "depends": [
        "bi_sql_editor",
        "crm",
        "qs2_marketing_suite_base",
        "web_pivot_computed_measure",
    ],
    "data": [
        "data/bi_sql_views.xml",
        "views/marketing_report_search.xml",
    ],
    "post_init_hook": "_post_init_apply_search_views",
    "installable": True,
}
