#!/usr/bin/env bash
#
# Faehrt den edulution Web-Installer non-interaktiv durch.
#
# Im normalen Betrieb klickt sich ein Mensch durch die Oberflaeche; das Skript
# `installer` blockiert so lange, bis der Web-Installer `edulution.env`
# geschrieben hat. Fuer den E2E-Lauf uebernehmen wir diesen Teil per API und
# erzeugen damit denselben Zustand, den die Oberflaeche erzeugen wuerde.
#
# Der letzte Aufruf (/api/finish) schreibt `edulution.env` und entsperrt das
# wartende Installer-Skript.

set -euo pipefail

BASE="${BASE_URL:-https://localhost:443}"
EDU_DOMAIN="${EDU_DOMAIN:-edulution.e2e.local}"
LMN_DOMAIN="${LMN_DOMAIN:-lmn.e2e.local}"
# createEdulutionEnvFile() schneidet den Root-DN per Regex aus diesem Wert
# heraus, der DN muss also einen DC=-Anteil besitzen.
BIND_DN="${BIND_DN:-CN=global-binduser,OU=Management,OU=GLOBAL,DC=linuxmuster,DC=lan}"
BIND_PW="${BIND_PW:-e2e-not-a-real-password}"
ADMIN_GROUP="${ADMIN_GROUP:-role-admin}"

log() { echo "[e2e] $*"; }

api() {
    local method="$1" path="$2"
    shift 2
    curl -sS --insecure --fail-with-body --max-time 120 \
        -X "${method}" "${BASE}${path}" "$@"
}

expect_ok() {
    local response="$1" step="$2"
    if [ "$(jq -r '.status' <<<"${response}")" != "true" ]; then
        echo "[e2e] FEHLER in Schritt '${step}':" >&2
        jq . <<<"${response}" >&2 || echo "${response}" >&2
        exit 1
    fi
    log "${step}: ok"
}

log "Warte auf den Web-Installer unter ${BASE} ..."
for attempt in $(seq 1 120); do
    if curl -sS --insecure --fail --max-time 10 -o /dev/null "${BASE}" 2>/dev/null; then
        log "Web-Installer erreichbar (nach ${attempt} Versuchen)"
        break
    fi
    if [ "${attempt}" -eq 120 ]; then
        echo "[e2e] Web-Installer wurde nicht erreichbar." >&2
        exit 1
    fi
    sleep 3
done

log "Sende Konfiguration (deploymentTarget=generic) ..."
response=$(api POST /api/configure -H 'Content-Type: application/json' -d @- <<JSON
{
  "organizationType": "school",
  "deploymentTarget": "generic",
  "lmnExternalDomain": "${LMN_DOMAIN}",
  "lmnBinduserDn": "${BIND_DN}",
  "lmnBinduserPw": "${BIND_PW}",
  "lmnLdapSchema": "ldap",
  "lmnLdapPort": 389,
  "edulutionExternalDomain": "${EDU_DOMAIN}",
  "lmnLocalInstall": false,
  "lmnWebuiPort": 8443
}
JSON
)
expect_ok "${response}" "configure"

log "Erzeuge selbstsigniertes Zertifikat ..."
response=$(api POST /api/create-ss-certificate -H 'Content-Type: application/json' -d @- <<JSON
{
  "countrycode": "DE",
  "state": "BW",
  "city": "CI",
  "organization": "edulution E2E",
  "valid_days": 30
}
JSON
)
expect_ok "${response}" "create-ss-certificate"

log "Setze Admin-Gruppe ..."
response=$(api POST /api/set-admin-group -H 'Content-Type: application/json' \
    -d "{\"admin_group\": \"${ADMIN_GROUP}\"}")
expect_ok "${response}" "set-admin-group"

log "Schliesse Web-Installation ab (schreibt edulution.env) ..."
response=$(api POST /api/finish)
expect_ok "${response}" "finish"

log "Web-Installer erfolgreich durchlaufen."
