# Messaggi verso App (`qs2_app_message`)

Mini client di posta interno a Odoo 19 che invia messaggi agli utenti (singoli o
per **lista di distribuzione**) e li espone a un **middleware esterno** tramite un
canale di notifica dedicato, riusando gli oggetti nativi `mail.message` e
`mail.notification`.

## Concetti

| Elemento | Implementazione |
|---|---|
| Subtype "Messaggio verso App" | `mail.message.subtype` → xmlid `qs2_app_message.mt_app_message` |
| Canale di consegna | `mail.notification.notification_type = 'app'` |
| Stato "inviato/consegnato" | `mail.notification.notification_status = 'sent'` |
| Messaggio composto (outbox) | modello `qs2.app.message` (eredita `mail.thread`) |
| Destinatari | un `res.users` **oppure** una `qs2.app.distribution.list` |

Quando un messaggio viene inviato (`action_send`):
1. viene pubblicato un `mail.message` sul record con il subtype dedicato;
2. viene creata una `mail.notification` per ogni destinatario con
   `notification_type='app'`, `notification_status='ready'`;
3. lo stato del record passa a **Inviato**; i destinatari vengono "congelati"
   nello snapshot `recipient_partner_ids`.

## Gruppi di sicurezza

- **Utente — invio messaggi App** (`group_app_message_user`): compone e invia.
- **Amministratore — Messaggi App** (`group_app_message_manager`): configura le
  liste di distribuzione (implica il gruppo Utente).
- **Middleware — Integrazione App** (`group_app_message_middleware`): account
  tecnico del middleware. Una `ir.rule` dedicata gli concede lettura/scrittura su
  **tutte** le notifiche `app` (la regola base limiterebbe ogni utente alle sole
  proprie notifiche).

> All'installazione, l'utente *admin* riceve il ruolo Amministratore.

## Contratto per il middleware (API esterna standard, no controller)

Autenticarsi (XML-RPC/JSON-RPC) con un utente nel gruppo
**Middleware — Integrazione App**.

### 1. Leggere i messaggi pendenti

Opzione A — helper dedicato:

```python
pending = models.execute_kw(db, uid, pwd,
    'mail.notification', 'app_fetch_pending', [100])
# -> [{notification_id, message_id, partner_id, partner_name,
#      user_id, login, subject, body, author, date}, ...]
```

Opzione B — query diretta:

```python
ids = models.execute_kw(db, uid, pwd, 'mail.notification', 'search', [[
    ['notification_type', '=', 'app'],
    ['notification_status', 'in', ['ready', 'process', 'pending']],
]])
rows = models.execute_kw(db, uid, pwd, 'mail.notification', 'read',
    [ids, ['res_partner_id', 'mail_message_id', 'notification_status']])
```

Il corpo del messaggio è `mail.message.body` (HTML), recuperabile via
`read`/`search_read` su `mail.message` usando `mail_message_id`.

### 2. Marcare come inviato/consegnato

Opzione A — helper dedicato:

```python
models.execute_kw(db, uid, pwd,
    'mail.notification', 'app_mark_sent', [notification_ids])
```

Opzione B — write diretta:

```python
models.execute_kw(db, uid, pwd, 'mail.notification', 'write',
    [notification_ids, {'notification_status': 'sent'}])
```

> Il middleware può scrivere **solo** `notification_status` (e affini): i campi
> `mail_message_id` / `res_partner_id` sono protetti dal core per i non-admin.

## Installazione (dev locale)

```bash
cd /home/leo/odoo19
./odoo-bin -c odoo.conf -d odoo19 -i qs2_app_message --stop-after-init   # install
./odoo-bin -c odoo.conf -d odoo19 -u qs2_app_message --stop-after-init   # upgrade
```
