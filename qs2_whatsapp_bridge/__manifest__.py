{
    "name": "WhatsApp Bridge",
    "version": "19.0.1.4.0",
    "category": "Discuss",
    "summary": "Invia e ricevi messaggi WhatsApp direttamente da Odoo",
    "description": """
WhatsApp Bridge per Odoo
========================

Integrazione WhatsApp personale (non Business API) tramite scansione
QR code, con interfaccia chat integrata in Odoo.

Architettura
------------
Il modulo comunica con un microservizio Node.js (il "bridge") che
gestisce la connessione a WhatsApp Web tramite Puppeteer.

::

    Odoo <-- HTTP --> Bridge Node.js <-- Puppeteer --> WhatsApp Web

Il bridge e' incluso nella cartella ``bridge/`` del modulo ed e'
deployabile su qualsiasi server Linux, Docker o cloud.

Prerequisiti
------------
* Node.js 22+ sul server dove gira il bridge
* Chromium/Chrome (installato automaticamente da Puppeteer)

Setup bridge — Opzione 1: systemd (consigliato)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

    # Trova il percorso del modulo installato
    cd /percorso/addons/qs2_whatsapp_bridge/bridge

    # Installa dipendenze + crea servizio systemd
    sudo ./setup.sh

    # Controlla i log (qui appare il QR code)
    journalctl -u qs2-whatsapp-bridge -f

    # Stato servizio
    systemctl status qs2-whatsapp-bridge

Setup bridge — Opzione 2: Docker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

    cd /percorso/addons/qs2_whatsapp_bridge/bridge
    docker compose up -d
    docker compose logs -f

Setup bridge — Opzione 3: manuale
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

    cd /percorso/addons/qs2_whatsapp_bridge/bridge
    npm install
    node server.js

Configurazione Odoo
-------------------
1. Avvia il bridge (vedi sopra)
2. In Odoo vai su **WhatsApp > Configurazione > Connessione**
3. Verifica che il Bridge URL sia corretto (default: http://localhost:3100)
4. Clicca **Aggiorna stato** — se il bridge e' su un altro server,
   modifica il Bridge URL prima
5. Scansiona il QR code con WhatsApp (Impostazioni > Dispositivi collegati)

Uso da altri moduli
-------------------
::

    # Invia un messaggio da qualsiasi modulo Odoo
    self.env['whatsapp.conversation'].send_message(
        phone='+39328...', body='Il tuo ordine e pronto!'
    )
    """,
    "author": "QuickStart2, Leonardo Guerra",
    "license": "AGPL-3",
    "depends": ["base", "contacts", "mail", "web", "crm", "sales_team"],
    "data": [
        "security/ir.model.access.csv",
        "data/whatsapp_cron.xml",
        "views/whatsapp_conversation_views.xml",
        "views/whatsapp_account_views.xml",
        "views/whatsapp_test_wizard_views.xml",
        "views/whatsapp_lead_wizard_views.xml",
        "views/res_partner_views.xml",
        "views/menu.xml",
        "views/whatsapp_template_views.xml",
        "data/whatsapp_template_seed.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "qs2_whatsapp_bridge/static/src/scss/whatsapp_chat.scss",
            "qs2_whatsapp_bridge/static/src/whatsapp_chat/whatsapp_chat.js",
            "qs2_whatsapp_bridge/static/src/whatsapp_chat/whatsapp_chat.xml",
            "qs2_whatsapp_bridge/static/src/chatter_button/chatter_button.js",
            "qs2_whatsapp_bridge/static/src/chatter_button/chatter_button.xml",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "icon": "/qs2_whatsapp_bridge/static/description/icon.png",
}
