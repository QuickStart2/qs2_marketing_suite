{
    "name": "Archiviazione sorgenti UTM",
    "summary": "Permette di archiviare e disarchiviare i record di utm.source",
    "description": """
Archiviazione sorgenti UTM
==========================

In Odoo standard i modelli ``utm.medium`` e ``utm.campaign`` hanno il campo
``active`` (quindi sono archiviabili), mentre ``utm.source`` no: le sorgenti
possono solo essere cancellate, cosa spesso impossibile perche' referenziate
da mailing, lead, ordini, ecc.

Questo modulo aggiunge ad ``utm.source``:

* il campo ``active`` (Attivo), con archiviazione/disarchiviazione dalla vista
  lista (menu Azioni) e dal form (interruttore + banda "Archiviato");
* il filtro "Archiviati" nella vista di ricerca, agganciato all'azione
  standard "Sorgenti".

Una sorgente archiviata resta valorizzata sui record che la usano, ma non e'
piu' proposta nei menu a tendina.
""",
    "version": "19.0.1.0.0",
    "category": "Marketing",
    "author": "Quickstart2 Srl",
    "website": "www.quickstart2.com",
    "license": "AGPL-3",
    "depends": ["utm"],
    "data": [
        "views/utm_source_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
