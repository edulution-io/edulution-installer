#!/bin/bash
set -e

# =============================================================================
# Edulution LMN Installer - Bootstrap
# =============================================================================
# Laedt alle Dateien von GitHub herunter, installiert Abhaengigkeiten
# und startet die API.
#
# Verwendung auf dem Zielserver:
#   curl -sSL https://raw.githubusercontent.com/hermanntoast/edulution-installer/main/edulution-lmninstaller/bootstrap.sh | bash
# =============================================================================

GITHUB_REPO="hermanntoast/edulution-installer"
GITHUB_BRANCH="main"
GITHUB_RAW="https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/edulution-lmninstaller"

INSTALL_DIR="/opt/edulution-installer"
VENV_DIR="${INSTALL_DIR}/venv"
API_HOST="0.0.0.0"
API_PORT="8000"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

install_system_packages() {
    log_info "Installing system packages..."

    if command -v apt-get &> /dev/null; then
        apt-get update -qq
        apt-get install -y -qq python3 python3-pip python3-venv ansible curl
    elif command -v dnf &> /dev/null; then
        dnf install -y -q python3 python3-pip ansible curl
    elif command -v yum &> /dev/null; then
        yum install -y -q python3 python3-pip ansible curl
    else
        log_error "No supported package manager found (apt, dnf, yum)"
        exit 1
    fi

    log_info "System packages installed"
}

setup_directory_structure() {
    log_info "Setting up directory structure..."

    mkdir -p "${INSTALL_DIR}/api/routes"
    mkdir -p "${INSTALL_DIR}/api/services"
    mkdir -p "${INSTALL_DIR}/playbooks/vars"
    mkdir -p "${INSTALL_DIR}/ansible/project"
    mkdir -p "${INSTALL_DIR}/ansible/inventory"

    log_info "Directory structure created"
}

download_file() {
    local remote_path="$1"
    local local_path="${INSTALL_DIR}/${remote_path}"

    mkdir -p "$(dirname "${local_path}")"

    if curl -sSfL "${GITHUB_RAW}/${remote_path}" -o "${local_path}"; then
        log_info "  ${remote_path}"
    else
        log_error "  Failed to download: ${remote_path}"
        return 1
    fi
}

download_files() {
    log_info "Downloading files from GitHub (${GITHUB_REPO}@${GITHUB_BRANCH})..."

    local files=(
        "requirements.txt"
        "api/__init__.py"
        "api/main.py"
        "api/config.py"
        "api/models.py"
        "api/routes/__init__.py"
        "api/routes/playbook.py"
        "api/routes/websocket.py"
        "api/services/__init__.py"
        "api/services/ansible_runner.py"
        "api/services/output_streamer.py"
        "playbooks/linuxmuster.yml"
        "playbooks/vars/linuxmuster_vars.yml"
    )

    for file in "${files[@]}"; do
        download_file "${file}"
    done

    log_info "All files downloaded"
}

setup_virtual_environment() {
    log_info "Setting up Python virtual environment..."

    python3 -m venv "${VENV_DIR}"
    source "${VENV_DIR}/bin/activate"

    pip install --upgrade pip -q
    pip install -r "${INSTALL_DIR}/requirements.txt" -q

    log_info "Virtual environment configured"
}

start_api_server() {
    # Alten Prozess stoppen falls vorhanden
    if [[ -f "${INSTALL_DIR}/api.pid" ]]; then
        local old_pid
        old_pid=$(cat "${INSTALL_DIR}/api.pid")
        if kill -0 "${old_pid}" 2>/dev/null; then
            log_info "Stopping existing API server (PID: ${old_pid})..."
            kill "${old_pid}" 2>/dev/null || true
            sleep 1
        fi
    fi

    log_info "Starting API server on ${API_HOST}:${API_PORT}..."

    cd "${INSTALL_DIR}"
    source "${VENV_DIR}/bin/activate"

    export PYTHONPATH="${INSTALL_DIR}"
    export EDULUTION_HOST="${API_HOST}"
    export EDULUTION_PORT="${API_PORT}"
    export EDULUTION_PLAYBOOK_DIR="${INSTALL_DIR}/playbooks"
    export EDULUTION_PRIVATE_DATA_DIR="${INSTALL_DIR}/ansible"

    nohup "${VENV_DIR}/bin/uvicorn" api.main:app \
        --host "${API_HOST}" \
        --port "${API_PORT}" \
        > "${INSTALL_DIR}/api.log" 2>&1 &

    API_PID=$!
    echo "${API_PID}" > "${INSTALL_DIR}/api.pid"

    sleep 2

    if kill -0 "${API_PID}" 2>/dev/null; then
        log_info "API server started (PID: ${API_PID})"
        log_info "API:       http://$(hostname -I | awk '{print $1}'):${API_PORT}"
        log_info "Health:    http://$(hostname -I | awk '{print $1}'):${API_PORT}/api/health"
        log_info "WebSocket: ws://$(hostname -I | awk '{print $1}'):${API_PORT}/ws/output"
    else
        log_error "Failed to start API server. Check ${INSTALL_DIR}/api.log"
        exit 1
    fi
}

main() {
    log_info "=== Edulution LMN Installer Bootstrap ==="

    check_root
    install_system_packages
    setup_directory_structure
    download_files
    setup_virtual_environment
    start_api_server

    log_info "=== Bootstrap completed ==="
}

main "$@"
