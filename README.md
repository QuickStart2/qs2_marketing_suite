# QS2 Marketing Suite for Odoo 19

> Dal click dell'inserzione al fatturato generato: suite di moduli Odoo 19 per la gestione completa del marketing — pianificazione media, tracciamento lead, inserzioni pubblicitarie, reportistica e messaggistica WhatsApp.

## Come si incastrano i moduli

La suite ricostruisce il funnel end-to-end attorno a un unico oggetto: **il lead CRM**.

| Fase | Modulo | Cosa aggiunge |
|------|--------|---------------|
| **Origine** | `qs2_marketing_suite_base` | Brand, Agenzie, Piani Media (budget e metriche), Inserzioni; campi marketing e rating sul lead |
| **Ingresso** | `qs2_lead_webhook` | Il click diventa un record: POST da landing page, Make, chatbot → lead, con routing automatico al venditore |
| **Comportamento** | `qs2_web_tracking` | Codice di tracking per contatto, visite web via `?track=CODE`, milestone di funnel |
| **Conversazione** | `qs2_whatsapp_bridge` | WhatsApp dentro Odoo, legato al contatto e al lead invece che al telefono del venditore |
| **Racconto** | `qs2_marketing_insights` | Tab "Storia": timeline unica inserzione → visite → chat → ordini → fatture → vinto/perso |
| **Aggregato** | `qs2_marketing_reports` | 3 report SQL che ricongiungono lead, piani media e vendite: budget speso contro fatturato |
| **Condivisione** | `qs2_crm_portal` | Area riservata per referenti esterni: consultano e aggiornano i propri lead da `/my`, senza backend |

Due moduli nel repo stanno **fuori** da questo filo:

- `qs2_app_message` — modulo indipendente (dipende solo da `mail`), nessun legame con il marketing. Ospitato qui, non parte della suite.
- `web_pivot_computed_measure` — **modulo OCA di terze parti** vendorizzato nel repo (vedi sotto).

---

## Moduli

### `qs2_marketing_suite_base` — Marketing Suite Base
**Application · v19.0.1.0.0 · dipende da:** `base`, `utm`, `crm`, `sales_team`

La radice della suite. Introduce le anagrafiche **Brand** e **Agenzie**, il **Piano Media** e le **Inserzioni**, e arricchisce il lead CRM con i campi marketing.

Il **Piano Media** (`qs2.media.plan`) è la riga di consuntivo per la combinazione campagna UTM + origine + mezzo + brand + mese/anno (combinazione unica per company). Inserisci a mano impressions, click e costo; il modulo incrocia il dato con i lead CRM collegati e calcola:

| Metrica | Formula |
|---------|---------|
| CTR % | `clicks / impressions × 100` |
| CPM | `cost / impressions × 1000` |
| CPC | `cost / clicks` |
| CPL | `cost / lead` |
| Conv. Rate % | `conversioni / lead × 100` |
| CPA | `cost / conversioni` |
| ROAS | `ricavo / cost` |

Tutte restituiscono **0** quando il denominatore è zero — mai un errore, mai un valore vuoto (attenzione: ROAS = 0 anche con ricavo > 0, se il costo è 0).

Sul lead aggiunge il tab **Marketing Insights** con la filiera completa (brand, agenzia, iniziativa, campagna, origine, mezzo, inserzione, piano media) e l'anteprima della creatività vista dal contatto. In più un **rating 0-5 stelle** calcolato da criteri configurabili: `(somma pesi criteri soddisfatti / somma pesi criteri attivi) × 5`. I criteri (`qs2.lead.rating.criterion`) si valutano in tre modi — campo valorizzato (`truthy`), campo uguale a un valore (`equals`), oppure il lead matcha un domain Odoo. All'install ne vengono creati 5 di default (email, telefono, azienda, inserzione tracciata, ricavo atteso > 1.000 €).

**Da sapere:**
- Il lead si collega al Piano Media **solo tramite un'inserzione**: `qs2_media_plan_id` è un related di `qs2_ad_id.media_plan_id`, non impostabile direttamente.
- Il campo **Ricavo non è fatturato reale**: è la somma di `expected_revenue` dei lead in stage con `is_won = True`.
- Il rating si ricalcola sui campi del lead, **non** al variare dei criteri: se aggiungi o modifichi un criterio, i lead esistenti restano al vecchio punteggio finché non vengono ri-scritti.
- I criteri di tipo `domain` fanno una `search_count` per ogni lead × ogni criterio: pesanti su ricalcoli massivi.

---

### `qs2_lead_webhook` — Lead Webhook
**v19.0.1.1.0 · dipende da:** `base`, `crm`, `sales_team`, `project`, `hr_recruitment`, `qs2_marketing_suite_base`

La porta d'ingresso dei lead. Espone 4 endpoint HTTP POST che permettono a sistemi esterni (Make/Integromat, chatbot, form di landing page) di creare record in Odoo. Mappa i parametri sui campi UTM standard **e** sui campi marketing QS2, poi un motore di regole (`qs2.lead.routing.rule`, configurabile da *CRM > Configurazione > Routing lead webhook*) assegna venditore e team senza hard-codare nulla nel controller.

| Endpoint | Auth | Cosa fa | Stato |
|----------|------|---------|-------|
| `POST /crm_lead_form/` | `public` | Crea un lead CRM da form esterno | Funzionante |
| `POST /crm_update_chatbot/` | `public` | Aggiorna un lead esistente identificato per telefono | Funzionante |
| `POST /assist_excel_form/` | `public` | Crea un `project.task` da Excel/form | Funzionante |
| `POST /crm_hr_form/` | `public` | Crea una candidatura HR (`hr.applicant`) | Funzionante |

> [!WARNING]
> **Tutti e 4 gli endpoint sono `auth="public"` con `csrf=False` e nessun token, firma o segreto condiviso.** Chiunque conosca l'URL può creare record, e la creazione avviene in `sudo()`. C'è anche un vettore di spam sulle anagrafiche: gli endpoint fanno get-or-create di `utm.source`, `utm.medium`, `utm.campaign` e `qs2.brand`, quindi POST ripetute possono gonfiare le tabelle di configurazione. Da mettere dietro reverse proxy con IP allowlist, rate limiting o token condiviso prima di esporre in produzione.

**Da sapere:**
- Se nessuna regola matcha e non è impostato il parametro `qs2_lead_webhook.default_user_id`, il lead resta **senza venditore**, quindi disponibile per l'assegnazione automatica del team. (Fino alla 19.0.1.0.0 ereditava il default di `crm.lead` e finiva assegnato al *Public user*, sparendo dall'assegnazione: corretto in 19.0.1.0.1.)
- Le regole di routing possono filtrare su **paese, provincia, CAP, lingua, origine UTM, brand e iniziativa**. Il paese va inviato come **codice ISO2** (`IT`, `FR`) o nome inglese; se assente ma la provincia è nota, viene dedotto da quella. La lingua è normalizzata contro quelle installate (`it` → `it_IT`).
- `description` del lead contiene un **dump integrale della POST** (tutti i parametri valorizzati, mappati e non): utile come audit, ma occhio a cosa ci finisce dentro.
- `/assist_excel_form/` crea `project.task` (richiede `project`, già in `depends`). Se è installata l'app FSM Enterprise, valorizza anche il *modello di foglio di lavoro*; su Community quel campo viene semplicemente ignorato. I dati extra del form finiscono nella descrizione del task.
- `/crm_hr_form/` crea `hr.applicant` (richiede `hr_recruitment`, già in `depends`). Il nome del candidato in Selezione del Personale è `nome_candidatura` (fallback su `nome_e_cognome`); origine su campi UTM standard; il resto del form nelle note della candidatura.

---

### `qs2_web_tracking` — Web Tracking
**v19.0.1.0.0 · dipende da:** `crm`, `phone_validation`, `website`

Assegna a ogni contatto un **codice di tracking di 12 caratteri** e lo usa per riconoscere le sue visite sul sito, tramite link personalizzati `https://sito/pagina?track=CODICE`. Ogni visita viene salvata (URL, timestamp, IP, user agent, referer, sessione) e confrontata con regole pattern-URL → **milestone**, che marcano il contatto quando raggiunge tappe commerciali (ha visto il webinar 2, ha guardato i prezzi).

Il risultato è `res.partner.qs2_milestone_ids`: il gancio su cui montare follow-up automatici con `base.automation`. In più normalizza i telefoni dei lead in E164 e garantisce che ogni lead abbia un contatto collegato.

Configurazione in *CRM > Configurazione*: Visite Web, Milestone tracking, Regole tracking.

> [!WARNING]
> Entrambe le route (`/qs2/activate`, `/qs2/pageview`) sono `auth='public'` con `csrf=False` e usano `sudo()`. `/qs2/activate` accetta qualunque `tracking_code` da chiunque: chi indovina o intercetta un codice può falsificare visite per quel contatto. L'ACL `access_qs2_visit_public` concede al gruppo pubblico **read + create** su `qs2.visit` senza record rule.

**Da sapere:**
- Il tracking gira su **tutte** le pagine frontend (sito web e portale), non solo sulle pagine del sito: `#wrapwrap` è definito in `web.frontend_layout`.
- I link con `?track=` **non vengono generati né inviati dal modulo**: il codice va letto dal contatto (scheda "Web Tracking", c'è il widget copia-negli-appunti) e messo a mano nelle email/SMS/WhatsApp.
- Il codice **non è alfanumerico**: è base64url in maiuscolo, quindi può contenere `-` e `_`. Resta URL-safe, che è ciò che serve al parametro `?track=`.
- Il `post_init_hook` fa il backfill dei codici con una write per record: lento su database con molti partner.

---

### `qs2_marketing_insights` — Marketing Insights
**v19.0.1.0.0 · dipende da:** `crm`, `mail`, `sale`, `qs2_marketing_suite_base`, `qs2_web_tracking`, `qs2_whatsapp_bridge`

Il collante narrativo della suite. Aggiunge al form del lead un tab **"Storia"**: una timeline verticale (widget OWL) che unifica in un unico flusso cronologico eventi normalmente sparsi su modelli diversi — origine UTM e inserzione cliccata, cambi di fase CRM, visite web e milestone, conversazioni WhatsApp, messaggi e note del chatter, attività, preventivi, ordini, fatture ed esito finale.

Serve a ricostruire a colpo d'occhio il percorso dal click al fatturato, senza navigare tra chatter, ordini, visite e chat.

> [!IMPORTANT]
> **L'integrazione con WhatsApp e Web Tracking è hard, non soft.** Nessun `hasattr`, nessun check su `ir.module`: il codice chiama direttamente `self.env['whatsapp.conversation']` e `self.env['qs2.visit']`. Conseguenza: installare il tab "Storia" **trascina dentro tutto il sito web** (via `qs2_web_tracking` → `website`) **e l'intero bridge WhatsApp**, anche se non li vuoi. Non esiste modo di avere la timeline senza WhatsApp.

Non richiede configurazione propria: non ha `data/`, non crea record, non ha hook. Perché la timeline sia popolata servono però le precondizioni dei moduli a monte (il lead deve avere `partner_id`, il tracking deve aver registrato visite, ecc.).

**Da sapere:** tutti gli aggregatori secondari usano `.sudo()`, quindi la timeline mostra dati che l'utente non vedrebbe altrove.

---

### `qs2_marketing_reports` — Marketing Reports
**v19.0.1.0.2 · dipende da:** `bi_sql_editor`, `crm`, `sale_crm`, `qs2_marketing_suite_base`, `web_pivot_computed_measure`

Modulo di **sola configurazione**: nessun modello, nessun Python applicativo. Precarica 3 report SQL basati su `bi_sql_editor` (OCA):

1. **Qualità lead** — motivi di perdita e lavorabilità
2. **Reportistica marketing** — funnel completo lead / budget / CPL / conversioni per mese
3. **Reportistica vendite** — fatturato per venditore

> [!IMPORTANT]
> **Non è utilizzabile subito dopo l'install.** Crea 3 record `bi.sql.view` in stato **bozza**: nessun modello, nessuna vista, nessun menu. Per ciascuno serve aprire il report e premere *Valida SQL > Crea modello > Crea interfaccia*. Solo dopo esiste il modello `x_bi_sql_view.marketing_report`; a quel punto va applicata **a mano** la search view `views/marketing_report_search.xml`, deliberatamente esclusa dal manifest proprio perché il modello non esiste prima.

**Da sapere:**
- La query legge `sale_order.opportunity_id`: da 19.0.1.0.2 `sale_crm` è dichiarato in `depends`, quindi installare la reportistica **tira dentro l'app Vendite** (voluto — prima il report andava in errore SQL su un DB senza vendite).
- Le query sono **PostgreSQL-specifiche**: `DATE_TRUNC`, `EXTRACT`, `regexp_replace`, `TO_DATE`, operatore jsonb `->>` per i campi tradotti.
- Il `regexp_replace` su `x_nome_lead` **non è un'anonimizzazione**: toglie solo punteggiatura e accenti, il nome resta in chiaro. I report espongono email e telefono dei lead in chiaro.
- La CTE `OrdFatt` scarta gli ordini con `amount_untaxed <= 10` e può gonfiare i conteggi per fan-out sul join.
- Dopo ogni *Crea Interfaccia*, `bi_sql_editor` rigenera la search view automatica e sovrascrive `search_view_id`: per ri-applicare quella custom va riscritto in due posti, sul `bi.sql.view` **e** sulla sua `action_id`.

---

### `qs2_crm_portal` — CRM Portal
**v19.0.1.0.0 · dipende da:** `crm`, `portal`, `qs2_marketing_suite_base`

Porta il CRM agli **utenti portale** con funzionalità ridotta: consultazione dei lead e aggiornamento dei soli dati di contatto, senza accesso al backend. Ogni lead ha un **Referente portale** (`qs2_portal_user_id`, un utente portale, assegnabile dal backend nella tab *Marketing Insights*). Quel referente, dalla sua area riservata, vede solo i lead a lui assegnati.

Route (tutte `auth="user"`):

| Route | Cosa fa |
|-------|---------|
| `/my` | Card "I miei lead" con contatore |
| `/my/leads` | Pipeline per fase (colonne) + KPI (totali, per fase) |
| `/my/leads/<id>` | Dettaglio + form di aggiornamento |
| `/my/leads/<id>/save` | Salvataggio (POST, CSRF) |

**Cosa può fare il referente:** aggiornare nome contatto, azienda, ruolo, email, telefono, indirizzo (via/città/CAP/provincia/paese) e iniziativa. **Non** può creare né cancellare lead, non vede né tocca i dati commerciali (valore atteso, probabilità, venditore), e lo **stage è in sola lettura** (niente drag&drop: la pipeline è statica).

**Sicurezza (a più livelli, verificata anche via RPC diretto):**
- **Righe** — record rule `crm_lead_rule_portal`: il portale vede solo i lead con `qs2_portal_user_id` = sé stesso. È l'**unico punto** da cambiare per adottare un altro perimetro (es. per azienda o team).
- **Campi in lettura** — `crm.lead._has_field_access`: fuori sudo e per un utente portale, la lettura è limitata a una whitelist; i dati commerciali restano invisibili *anche sui propri lead*, anche via RPC.
- **Campi in scrittura** — ACL read-only + il salvataggio passa dal controller, che scrive in `sudo()` un dict **solo whitelisted** (anti mass-assignment). Un POST che inietta campi vietati viene ignorato.
- **No propagazione al partner** — email/telefono si salvano sul lead ma **non** si riversano sul `res.partner` collegato (flag `qs2_portal_no_partner_sync` che neutralizza gli inverse del core): un referente non può modificare un contatto su cui non ha diritti.

**Da sapere:**
- Il perimetro scelto è "referente esplicito". Serve popolare `qs2_portal_user_id` sui lead (a mano o via automazione) perché un portale veda qualcosa.
- Cambiando il paese nel form, l'elenco province si aggiorna al salvataggio; una provincia non coerente col paese scelto viene scartata lato server.
- L'aspetto è "simile al CRM" ma **non** è il kanban del backend (drag&drop, quick-create, inline edit): quelli vivono nel web client interno, non disponibile ai portali.

---

### `qs2_whatsapp_bridge` — WhatsApp Bridge
**Application · v19.0.1.4.1 · dipende da:** `base`, `contacts`, `mail`, `web`, `crm`, `sales_team`

Integra WhatsApp **personale** (non la Business API ufficiale) dentro Odoo: colleghi un numero scansionando un QR code e da lì invii e ricevi messaggi senza uscire da Odoo, con una UI chat in stile WhatsApp Web e template riusabili. Le conversazioni restano legate al contatto e al lead invece che al telefono del venditore.

Non parla direttamente con Meta: si appoggia a un **microservizio Node.js incluso nel modulo** (`bridge/`) che pilota WhatsApp Web via Puppeteer/`whatsapp-web.js`, e che Odoo interroga in HTTP. Espone 8 route JSON-RPC `auth="user"` (`/whatsapp/status`, `/qr`, `/send`, `/conversations`, `/archive`, `/messages`, `/new_conversation`, `/poll_bridge`) e un cron **"WhatsApp: ricevi messaggi"** attivo di default ogni minuto.

**Requisiti del bridge:** Node.js 22+ (`setup.sh` rifiuta versioni inferiori), npm, Chromium/Chrome per Puppeteer, accesso in uscita a `raw.githubusercontent.com/wppconnect-team/wa-version` (il bridge usa `webVersionCache` remoto). Setup: `cd qs2_whatsapp_bridge/bridge && npm install`, poi `sudo ./setup.sh` (systemd) o il Dockerfile fornito.

> [!CAUTION]
> **Il bridge Node.js non ha alcuna autenticazione**: `/status`, `/qr`, `/send`, `/messages`, `/stream` sono aperti a chi raggiunge la porta. Non esporlo in rete — bind su localhost o rete interna.
>
> **La sessione WhatsApp è un profilo Chrome completo con le credenziali** in `bridge/auth_state/`. È coperto dal `.gitignore`: non committarlo mai, per nessun motivo. Chi ottiene quella cartella può impersonare il numero collegato.
>
> **`/whatsapp/qr` è leggibile da qualsiasi utente interno**: durante il pairing chi legge il QR può scansionarlo col proprio telefono e agganciare il bridge al proprio numero. Il menu WhatsApp non ha `groups_id` — visibile a tutti gli utenti interni.
>
> Non essendo la Business API ufficiale, l'uso è soggetto ai **rischi di ToS e ban** di WhatsApp.

**Da sapere:**
- **All'install il modulo fa una chiamata di rete**: il `post_init_hook` crea l'account e fa una GET sul bridge.
- Le immagini ricevute vengono salvate ma **non** mostrate in chat: il template OWL renderizza solo `msg.body`.
- Due percorsi di ricezione divergenti sulla stessa coda: il cron **non** gestisce gli allegati, il poll dal frontend sì.

---

### `qs2_app_message` — Messaggi verso App
**Application · v19.0.1.0.0 · dipende da:** `mail`

> [!NOTE]
> Modulo **indipendente**, ospitato in questo repo ma estraneo al funnel marketing: zero riferimenti a `crm` o ai modelli `qs2_*` della suite.

Mini client di posta interno: componi messaggi e recapitali agli utenti (interni o portale) di un'app esterna, scegliendo come destinatario un singolo utente o una **lista di distribuzione** custom. Invece di inventare un modello parallelo riusa `mail.message` e `mail.notification`, aggiungendo un canale di consegna dedicato (`app`) e un subtype proprio, così lo stato di consegna sfrutta la macchina a stati nativa di Odoo. Include un cron per l'invio programmato.

**Il middleware non è incluso**: il modulo è solo il lato Odoo, non espone controller HTTP. Un componente esterno (da realizzare) si autentica via XML-RPC/JSON-RPC standard e consuma `mail.notification.app_fetch_pending` / `app_mark_sent`. Per funzionare serve creare un utente tecnico e assegnargli il gruppo **"Middleware — Integrazione App"** (nessuno lo riceve all'install).

**Da sapere:**
- La ir.rule del middleware concede lettura **e scrittura su tutte** le `mail.notification`, e il gruppo implica `base.group_user`: l'account middleware è un utente interno a tutti gli effetti (consuma una licenza ed eredita i permessi base).
- Semantica core fuorviante: in Odoo 19 `notification_status` ha `pending` etichettato "Sent" e `sent` etichettato "Delivered".

---

### `web_pivot_computed_measure` — Web Pivot Computed Measure
**Terze parti (OCA) · v19.0.1.0.0 · dipende da:** `web`

> [!NOTE]
> **Non è codice QS2.** È una copia vendorizzata di [OCA/web](https://github.com/OCA/web) (Tecnativa — Alexandre Díaz, maintainer CarlosRoca13), inclusa nel repo perché è dipendenza hard di `qs2_marketing_reports`. Va aggiornata da upstream, **non modificata in place**.

Modulo puramente frontend (OWL/JS): aggiunge alla vista pivot la possibilità di creare **misure calcolate** al volo, combinando due misure esistenti con un'operazione aritmetica (somma, sottrazione, moltiplicazione, divisione, percentuale). La misura è un campo finto lato client — non esiste nel DB, viene calcolata nel browser su ogni cella. Evita di dover creare campi computed in Python solo per vedere un rapporto tra due colonne già nel pivot.

Nessuna configurazione: patcha globalmente il pivot, la voce "Computed Measure" compare in tutte le viste pivot di tutti i moduli.

**Da sapere:** il README upstream dice che la formula è valutata con `PY.eval` — **è falso**, il codice usa un parser aritmetico proprio. L'opzione "Custom" (formula libera) è di fatto irraggiungibile dalla UI (condizionata a `t-if="debug"`).

---

## Installazione

### Dipendenze da procurare a parte

| Cosa | Dove | Serve a |
|------|------|---------|
| **`bi_sql_editor`** | [OCA/reporting-engine](https://github.com/OCA/reporting-engine) branch `19.0` — **non incluso nel repo** | `qs2_marketing_reports` (dipendenza hard) |
| **Node.js 22+, npm, Chromium** | sul server che ospita il bridge | `qs2_whatsapp_bridge` |
| **Odoo Enterprise** (opzionale) | — | `/assist_excel_form/` valorizza il *modello foglio di lavoro* FSM solo se presente; senza, il campo è ignorato |

> [!TIP]
> Asimmetria che confonde: `qs2_marketing_reports` ha due dipendenze OCA, ma `web_pivot_computed_measure` è **dentro** il repo e `bi_sql_editor` **no**. Se l'install fallisce con *module not found*, è quasi sempre `bi_sql_editor` che manca dagli `addons_path`.

### Ordine consigliato

1. **`web_pivot_computed_measure`** — OCA già nel repo, nessuna dipendenza QS2
2. **`bi_sql_editor`** — OCA esterno, negli `addons_path`
3. **`qs2_marketing_suite_base`** — la radice: 3 dei 4 moduli QS2 restanti lo richiedono
4. **`qs2_web_tracking`** — autonomo, ma va prima di insights. Tira dentro `website` (tutto il sito Odoo)
5. **`qs2_whatsapp_bridge`** — autonomo, ma va prima di insights. Inerte finché il microservizio Node non è in piedi
6. **`qs2_lead_webhook`** — la porta d'ingresso dei lead
7. **`qs2_marketing_insights`** — il più vincolato: richiede base + tracking + whatsapp, e tira dentro `sale`
8. **`qs2_marketing_reports`** — ultimo: richiede i due OCA. **Post-install manuale** (vedi la sua sezione)
9. **`qs2_crm_portal`** — dopo il base QS2: aggiunge l'area portale ai lead
10. **`qs2_app_message`** — quando vuoi, è indipendente

**Scorciatoia:** installare `qs2_marketing_insights` tira dentro automaticamente base + tracking + whatsapp + sale. Restano fuori solo webhook, reports e portal.

`qs2_web_tracking` e `qs2_whatsapp_bridge` **non** dipendono dal base QS2: sono usabili stand-alone. Presi da soli però i loro dati non confluiscono da nessuna parte — è `qs2_marketing_insights` a ricucirli.

---

## Sicurezza

Prima di andare in produzione, i punti che richiedono una scelta consapevole:

- **`qs2_lead_webhook`** — 4 endpoint `auth="public"`, `csrf=False`, senza token, che creano record in `sudo()`. Metti reverse proxy + IP allowlist o token condiviso.
- **`qs2_web_tracking`** — 2 route `auth="public"` in `sudo()`; il gruppo pubblico ha read + create su `qs2.visit` senza record rule.
- **`qs2_whatsapp_bridge`** — il microservizio Node **non ha autenticazione**: bind su localhost. La sessione in `bridge/auth_state/` sono credenziali a tutti gli effetti: mai in git. `/whatsapp/qr` è leggibile da ogni utente interno.
- **`qs2_marketing_reports`** — i report SQL espongono email e telefono dei lead in chiaro a chi ha accesso al report.
- **`qs2_app_message`** — il gruppo middleware ha read/write su **tutte** le `mail.notification` ed è un utente interno.
- **`qs2_crm_portal`** — espone i lead a utenti portale: la tenuta dipende dal campo `qs2_portal_user_id` (chi lo popola decide chi vede cosa) e dalla whitelist di campi. Isolamento righe/campi e blocco propagazione al partner sono verificati anche via RPC; il perimetro è un solo `domain_force` da rivedere se cambia la strategia di visibilità.

---

## Note di sviluppo

- **Versioni per-modulo.** Ogni modulo ha la sua versione (`qs2_lead_webhook` è a `19.0.1.1.0`, `qs2_whatsapp_bridge` a `19.0.1.4.1`, gli altri sulla linea `19.0.1.0.x`). Su Odoo.sh il bump di versione è ciò che triggera `-u`: incrementa la versione del modulo su ogni commit che lo tocca, o l'aggiornamento non parte.
- **Artefatti runtime.** `bridge/auth_state/`, `bridge/node_modules/`, `.wwebjs_cache/` e i log sono gitignored e non vanno committati: contengono credenziali o sono rigenerabili.

## Licenza

Tutti i moduli sono **AGPL-3**, coerentemente con il `LICENSE` del repo e con l'AGPL-3 di `web_pivot_computed_measure`. Nessun conflitto — ma l'AGPL è virale sui deploy SaaS: se offri questi moduli come servizio in rete, sei tenuto a rendere disponibile il sorgente delle tue modifiche.
