#!/usr/bin/env bash
# ============================================================================
# QS2 WhatsApp Bridge — Setup & Install
#
# Questo script:
#   1. Verifica i prerequisiti (Node.js 22+, npm)
#   2. Installa le dipendenze Node.js
#   3. Crea un servizio systemd per avviare il bridge automaticamente
#   4. Avvia il servizio
#
# Uso:
#   chmod +x setup.sh
#   sudo ./setup.sh                    # installazione standard (porta 3100)
#   sudo ./setup.sh --port 3200       # porta personalizzata
#   sudo ./setup.sh --uninstall       # rimuove il servizio
#
# Dopo l'installazione:
#   - Il bridge gira come servizio systemd "qs2-whatsapp-bridge"
#   - Si avvia automaticamente al boot
#   - Logs: journalctl -u qs2-whatsapp-bridge -f
#   - Per il QR code: journalctl -u qs2-whatsapp-bridge --no-pager | tail -40
#
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="qs2-whatsapp-bridge"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
DEFAULT_PORT=3100
PORT="${DEFAULT_PORT}"
RUN_USER="${SUDO_USER:-$(whoami)}"
AUTH_DIR="${SCRIPT_DIR}/auth_state"

# ============================================================================
# Parse argomenti
# ============================================================================
UNINSTALL=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            PORT="$2"
            shift 2
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        *)
            echo "Uso: sudo $0 [--port PORTA] [--uninstall]"
            exit 1
            ;;
    esac
done

# ============================================================================
# Uninstall
# ============================================================================
if [ "$UNINSTALL" = true ]; then
    echo "Rimozione servizio ${SERVICE_NAME}..."
    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
    rm -f "${SERVICE_FILE}"
    systemctl daemon-reload
    echo "Servizio rimosso. I dati di autenticazione restano in ${AUTH_DIR}"
    exit 0
fi

# ============================================================================
# Prerequisiti
# ============================================================================
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  QS2 WhatsApp Bridge — Setup             ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Node.js
if ! command -v node &>/dev/null; then
    echo "ERRORE: Node.js non trovato."
    echo "Installa Node.js 22+: https://nodejs.org/"
    echo ""
    echo "Su Ubuntu/Debian:"
    echo "  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
    echo "  sudo apt-get install -y nodejs"
    exit 1
fi

NODE_MAJOR=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 22 ]; then
    echo "ERRORE: Node.js $(node -v) — serve v22+. Aggiorna Node.js."
    exit 1
fi
echo "[OK] Node.js $(node -v)"

# npm
if ! command -v npm &>/dev/null; then
    echo "ERRORE: npm non trovato."
    exit 1
fi
echo "[OK] npm $(npm -v)"

# Root check per systemd
if [ "$(id -u)" -ne 0 ]; then
    echo ""
    echo "ATTENZIONE: Per creare il servizio systemd serve sudo."
    echo "  sudo $0 $*"
    echo ""
    echo "Oppure installa solo le dipendenze senza servizio:"
    echo "  cd ${SCRIPT_DIR} && npm install"
    echo "  node server.js"
    exit 1
fi

# ============================================================================
# Installazione dipendenze
# ============================================================================
echo ""
echo "Installazione dipendenze Node.js..."
cd "${SCRIPT_DIR}"
sudo -u "${RUN_USER}" npm install --production 2>&1 | tail -3
echo "[OK] Dipendenze installate"

# ============================================================================
# Creazione directory auth
# ============================================================================
mkdir -p "${AUTH_DIR}"
chown "${RUN_USER}:${RUN_USER}" "${AUTH_DIR}"

# ============================================================================
# Creazione servizio systemd
# ============================================================================
echo ""
echo "Creazione servizio systemd: ${SERVICE_NAME}"

NODE_PATH="$(which node)"

cat > "${SERVICE_FILE}" << UNIT
[Unit]
Description=QS2 WhatsApp Bridge
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${SCRIPT_DIR}
Environment=WA_BRIDGE_PORT=${PORT}
Environment=WA_AUTH_PATH=${AUTH_DIR}
Environment=NODE_ENV=production
ExecStart=${NODE_PATH} ${SCRIPT_DIR}/server.js
Restart=on-failure
RestartSec=10

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=${AUTH_DIR} ${SCRIPT_DIR}/node_modules
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

# ============================================================================
# Avvio servizio
# ============================================================================
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "[OK] Servizio creato e avviato"

# ============================================================================
# Verifica
# ============================================================================
sleep 5
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║  Bridge avviato con successo!             ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""
    echo "  URL:     http://localhost:${PORT}"
    echo "  Servizio: ${SERVICE_NAME}"
    echo "  Auth:    ${AUTH_DIR}"
    echo ""
    echo "  Comandi utili:"
    echo "    systemctl status ${SERVICE_NAME}"
    echo "    systemctl restart ${SERVICE_NAME}"
    echo "    journalctl -u ${SERVICE_NAME} -f"
    echo ""
    echo "  Per vedere il QR code:"
    echo "    journalctl -u ${SERVICE_NAME} --no-pager | tail -40"
    echo ""
    echo "  Per disinstallare:"
    echo "    sudo $0 --uninstall"
    echo ""
else
    echo ""
    echo "ATTENZIONE: Il servizio non si e' avviato correttamente."
    echo "Controlla i log: journalctl -u ${SERVICE_NAME} --no-pager -n 30"
fi
