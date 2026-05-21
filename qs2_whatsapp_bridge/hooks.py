import logging

_logger = logging.getLogger(__name__)

BRIDGE_SETUP_MSG = """
<h3>WhatsApp Bridge — Setup richiesto</h3>
<p>Il modulo WhatsApp Bridge e' stato installato, ma il <b>bridge Node.js</b>
non e' raggiungibile.</p>

<p>Il bridge e' un microservizio separato che gestisce la connessione
a WhatsApp Web. Senza di esso, il modulo non puo' inviare/ricevere messaggi.</p>

<h4>Setup rapido (Linux con systemd)</h4>
<pre>
# Vai nella cartella bridge del modulo
cd {bridge_path}

# Installa e crea il servizio (richiede sudo)
sudo ./setup.sh

# Controlla i log per il QR code
journalctl -u qs2-whatsapp-bridge -f
</pre>

<h4>Setup con Docker</h4>
<pre>
cd {bridge_path}
docker compose up -d
docker compose logs -f
</pre>

<h4>Setup manuale</h4>
<pre>
cd {bridge_path}
npm install
node server.js
</pre>

<p>Dopo l'avvio, vai su <b>WhatsApp > Configurazione > Connessione</b>
per scansionare il QR code e verificare lo stato.</p>
"""


def post_init_hook(env):
    """Verifica che il bridge sia raggiungibile dopo l'installazione."""
    import os
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    account = env["whatsapp.account"].sudo().search([], limit=1)
    if not account:
        account = env["whatsapp.account"].sudo().create({"name": "WhatsApp"})

    bridge_url = account.bridge_url or "http://localhost:3100"
    bridge_reachable = False

    try:
        req = Request(f"{bridge_url}/status")
        with urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                bridge_reachable = True
    except (URLError, ConnectionError, OSError):
        pass

    if bridge_reachable:
        _logger.info("WhatsApp Bridge raggiungibile su %s", bridge_url)
        account.action_refresh_status()
    else:
        # Trova il path del bridge per le istruzioni
        bridge_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "bridge"
        )
        _logger.warning(
            "WhatsApp Bridge NON raggiungibile su %s. "
            "Avvia il bridge con: cd %s && sudo ./setup.sh",
            bridge_url,
            bridge_path,
        )
        # Lascia un messaggio nel chatter dell'account (se ha mail.message)
        try:
            env["mail.message"].sudo().create([{
                "model": "whatsapp.account",
                "res_id": account.id,
                "message_type": "comment",
                "body": BRIDGE_SETUP_MSG.format(bridge_path=bridge_path),
            }])
        except Exception:
            pass  # whatsapp.account potrebbe non ereditare mail.thread
