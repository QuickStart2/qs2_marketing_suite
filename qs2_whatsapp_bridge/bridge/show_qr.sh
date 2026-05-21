#!/usr/bin/env bash
# ============================================================================
# QS2 WhatsApp Bridge — Mostra QR Code per scansione
#
# Scarica il QR dal bridge (http://localhost:3100/qr), lo salva come PNG
# in /tmp/qs2-whatsapp-qr.png e lo apre con Anteprima (macOS `open`).
#
# Uso:
#   ./show_qr.sh              # mostra una volta
#   ./show_qr.sh --watch      # rigenera ogni 5s finche' non connesso
# ============================================================================
set -euo pipefail

BRIDGE_URL="${BRIDGE_URL:-http://localhost:3100}"
QR_FILE="/tmp/qs2-whatsapp-qr.png"

fetch_and_show() {
    local status_json
    status_json="$(curl -fsS "${BRIDGE_URL}/status" 2>/dev/null || echo '{"status":"unreachable"}')"
    local status
    status="$(echo "${status_json}" | sed -E 's/.*"status":"([^"]+)".*/\1/')"

    case "${status}" in
        connected)
            echo "✔  WhatsApp gia' connesso — nessun QR da mostrare."
            return 0
            ;;
        unreachable)
            echo "ERRORE: bridge non raggiungibile su ${BRIDGE_URL}"
            echo "Verifica: launchctl list | grep qs2-whatsapp-bridge"
            return 1
            ;;
        qr|disconnected)
            ;;
        *)
            echo "Stato bridge sconosciuto: ${status}"
            ;;
    esac

    local qr_json
    qr_json="$(curl -fsS "${BRIDGE_URL}/qr" 2>/dev/null || echo '')"
    if [ -z "${qr_json}" ] || ! echo "${qr_json}" | grep -q '"qr"'; then
        echo "QR non ancora disponibile (stato: ${status}). Attendi qualche secondo..."
        return 2
    fi

    echo "${qr_json}" \
        | sed -E 's/.*"qr":"data:image\/png;base64,([^"]+)".*/\1/' \
        | base64 -d > "${QR_FILE}"

    echo "QR salvato in ${QR_FILE} — apertura con Anteprima..."
    open "${QR_FILE}"
    echo ""
    echo "📱 Su WhatsApp del telefono:"
    echo "   Impostazioni → Dispositivi collegati → Collega dispositivo"
    echo "   Inquadra il QR sullo schermo del Mac."
    return 0
}

if [ "${1:-}" = "--watch" ]; then
    echo "Watch mode: rigenero QR ogni 5s finche' non connesso (Ctrl+C per uscire)"
    while true; do
        status="$(curl -fsS "${BRIDGE_URL}/status" 2>/dev/null | sed -E 's/.*"status":"([^"]+)".*/\1/' || echo "unreachable")"
        if [ "${status}" = "connected" ]; then
            echo ""
            echo "✔  Connesso! Puoi chiudere Anteprima."
            break
        fi
        fetch_and_show || true
        sleep 5
    done
else
    fetch_and_show
fi
