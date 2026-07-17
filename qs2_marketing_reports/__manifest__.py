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
    "version": "19.0.1.0.1",
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
    ],
    # NB: la search view PWR (views/marketing_report_search.xml) NON è caricata
    # all'install perché punta al modello x_bi_sql_view.marketing_report che
    # esiste solo DOPO "Crea Modello/Interfaccia" in bi_sql_editor. Va applicata
    # a valle della validazione del report (vedi README / script di setup).
    "installable": True,
}
