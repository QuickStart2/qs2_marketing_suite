{
    "name": "Messaggi verso App",
    "summary": "Mini client di posta interno: invia messaggi agli utenti (singoli o liste) "
               "letti da un middleware esterno tramite un canale di notifica dedicato.",
    "description": """
Messaggi verso App
==================

Si appoggia agli oggetti nativi ``mail.message`` / ``mail.notification`` aggiungendo:

- un **subtype** dedicato "Messaggio verso App";
- un **canale di notifica** ``app`` (``mail.notification.notification_type = 'app'``);
- un mini client di posta (modello ``qs2.app.message``) per comporre e inviare
  messaggi a un **utente singolo** o a una **lista di distribuzione** custom;
- gruppi di sicurezza dedicati: chi puo' inviare, chi configura, e l'account del
  middleware esterno che marca i messaggi come "inviati".

Il middleware legge le notifiche pendenti (``notification_type = 'app'``,
``notification_status in ('ready','process','pending')``) via API esterna standard
(XML-RPC / JSON-RPC) e scrive ``notification_status = 'sent'`` quando consegnati.
Vedi README.md per il contratto RPC.
    """,
    "version": "19.0.1.0.0",
    "category": "Productivity/Discuss",
    "author": "QuickStart2, Leonardo Guerra",
    "website": "www.quickstart2.com",
    "license": "AGPL-3",
    "depends": ["mail"],
    "data": [
        "security/qs2_app_message_groups.xml",
        "security/ir.model.access.csv",
        "security/qs2_app_message_rules.xml",
        "data/mail_message_subtype.xml",
        "data/ir_cron.xml",
        "views/qs2_app_distribution_list_views.xml",
        "views/qs2_app_message_views.xml",
        "views/mail_notification_views.xml",
        "views/qs2_app_message_menus.xml",
    ],
    "application": True,
    "installable": True,
}
