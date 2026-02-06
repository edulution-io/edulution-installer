#!/bin/bash
set -e

# =============================================================================
# Edulution LMN Installer - Client Script
# =============================================================================
# Fuehre dieses Script auf deinem Client aus. Es verbindet sich per SSH
# mit dem Zielserver, laedt den Bootstrap von GitHub und startet die API.
#
# Verwendung:
#   ./install.sh root@10.0.0.1
#   ./install.sh root@meinserver.example.com
#
# Danach:
#   curl http://10.0.0.1:8000/api/health
# =============================================================================

GITHUB_REPO="hermanntoast/edulution-installer"
GITHUB_BRANCH="main"
BOOTSTRAP_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/bootstrap.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    echo "Verwendung: $0 <user@host>"
    echo ""
    echo "Beispiele:"
    echo "  $0 root@10.0.0.1"
    echo "  $0 root@meinserver.example.com"
    echo ""
    echo "Das Script verbindet sich per SSH zum Zielserver,"
    echo "laedt den Installer von GitHub herunter und startet die API."
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

SSH_TARGET="$1"

# Host-Teil aus user@host extrahieren
SERVER_HOST="${SSH_TARGET#*@}"

log_info "=== Edulution LMN Installer ==="
log_info "Zielserver: ${SSH_TARGET}"
log_info ""

# Verbindung testen
log_info "Teste SSH-Verbindung..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "${SSH_TARGET}" 'echo ok' > /dev/null 2>&1; then
    log_error "SSH-Verbindung zu ${SSH_TARGET} fehlgeschlagen."
    log_error "Stelle sicher, dass:"
    log_error "  - Der Server erreichbar ist"
    log_error "  - SSH-Key hinterlegt ist (ssh-copy-id ${SSH_TARGET})"
    exit 1
fi
log_info "SSH-Verbindung OK"

# Bootstrap ausfuehren
log_info "Starte Bootstrap auf ${SSH_TARGET}..."
ssh -t "${SSH_TARGET}" "curl -sSL ${BOOTSTRAP_URL} | bash"

# API testen
log_info "Warte auf API..."
for i in $(seq 1 15); do
    if curl -s "http://${SERVER_HOST}:8000/api/health" > /dev/null 2>&1; then
        log_info "API ist bereit!"
        echo ""
        log_info "=== Installation bereit ==="
        log_info ""
        log_info "API:       http://${SERVER_HOST}:8000"
        log_info "Health:    http://${SERVER_HOST}:8000/api/health"
        log_info "Status:    http://${SERVER_HOST}:8000/api/status"
        log_info "WebSocket: ws://${SERVER_HOST}:8000/ws/output"
        log_info ""
        log_info "Playbook starten:"
        log_info "  curl -X POST http://${SERVER_HOST}:8000/api/playbook/start \\"
        log_info "    -H 'Content-Type: application/json' \\"
        log_info "    -d '{\"playbook\": \"linuxmuster.yml\", \"variables\": {\"extra_vars\": {\"lmn_schoolname\": \"Meine Schule\", \"lmn_adminpw\": \"Muster!\"}}}'"
        log_info ""
        log_info "Output verfolgen:"
        log_info "  websocat ws://${SERVER_HOST}:8000/ws/output"
        exit 0
    fi
    sleep 1
done

log_error "API antwortet nicht auf http://${SERVER_HOST}:8000"
log_error "Pruefe Logs: ssh ${SSH_TARGET} 'cat /opt/edulution-installer/api.log'"
exit 1
