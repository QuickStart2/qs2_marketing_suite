# Archiviazione sorgenti UTM (`qs2_utm_source_archive`)

Odoo 19 — rende archiviabili i record di `utm.source`.

## Perche'

In Odoo standard `utm.medium` e `utm.campaign` hanno il campo `active` e quindi
sono archiviabili; `utm.source` no. Le sorgenti si possono solo cancellare, ma
la cancellazione e' quasi sempre bloccata perche' `utm.source.mixin.source_id`
e' `ondelete='restrict'` (mailing, social post, ...) e perche' la sorgente e'
referenziata da lead, ordini e link tracker.

## Cosa fa

* Aggiunge `active` (etichetta **Attivo**) a `utm.source`, default `True`
  (tutte le sorgenti esistenti restano attive dopo l'aggiornamento).
* Vista lista: il campo `active` nascosto abilita le azioni
  **Archivia / Annulla archiviazione** dal menu Azioni sulla selezione multipla.
* Vista form: interruttore **Attivo** + banda **Archiviato**.
* Nuova vista di ricerca con filtro **Archiviati**, agganciata all'azione
  standard `utm.utm_source_action` ("Sorgenti").

## Note tecniche

### Le sorgenti esistenti devono restare attive (`post_init_hook`)

Aggiungendo `active` a un modello gia' popolato, Odoo esegue
`ALTER TABLE utm_source ADD COLUMN active boolean DEFAULT false`
(`odoo/tools/sql.py::create_column`): PostgreSQL valorizza le righe esistenti a
`false`, non a `NULL`. Il successivo `_init_column` (`odoo/orm/models.py`) scrive
il default `True` solo `WHERE active IS NULL`, quindi non aggancia nessuna riga.

Senza correzione **tutte le sorgenti gia' presenti nascerebbero archiviate**.
Il modulo lo evita con un `post_init_hook` (`hooks.py`) che le riporta ad
`active = TRUE`. L'hook gira solo all'installazione, non agli update
(`odoo/modules/loading.py`), quindi non riattiva cio' che l'utente archivia.

### Vincolo UNIQUE(name) e sorgenti archiviate

`utm.source` ha un vincolo `UNIQUE(name)` a livello di database, che vale anche
per i record archiviati. Il calcolo del nome univoco fatto da
`utm.mixin._get_unique_names` usa una `search_read` soggetta ad `active_test`:
senza correzione, creare una sorgente con lo stesso nome di una archiviata non
avrebbe ricevuto il contatore (`Nome [2]`) e sarebbe fallita con `IntegrityError`.
Il modulo forza `active_test=False` in quel controllo per `utm.source`
(`models/utm_mixin.py`).

Il tracciamento UTM in ingresso non e' impattato: `utm.mixin._find_or_create_record`
cerca gia' con `active_test=False`, quindi una sorgente archiviata viene
riutilizzata invece di generare un duplicato.

## Installazione

Modulo indipendente, dipende solo da `utm`.

    -i qs2_utm_source_archive
