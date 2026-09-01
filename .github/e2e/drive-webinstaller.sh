#!/usr/bin/env bash
#
# Drives the edulution web installer non-interactively.
#
# Normally a human clicks through the interface and the `installer` script
# blocks until the web installer has written `edulution.env`. For the E2E run
# we take that part over via the API and produce the same state the interface
# would produce.
#
# The last call (/api/finish) writes `edulution.env` and releases the waiting
# installer script.

set -euo pipefail

BASE="${BASE_URL:-https://localhost:443}"
EDU_DOMAIN="${EDU_DOMAIN:-edulution.e2e.local}"
LMN_DOMAIN="${LMN_DOMAIN:-lmn.e2e.local}"
# createEdulutionEnvFile() carves the root DN out of this value with a regex,
# so the DN has to contain a DC= part.
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
        echo "[e2e] step '${step}' failed:" >&2
        jq . <<<"${response}" >&2 || echo "${response}" >&2
        exit 1
    fi
    log "${step}: ok"
}

log "Waiting for the web installer at ${BASE} ..."
for attempt in $(seq 1 120); do
    if curl -sS --insecure --fail --max-time 10 -o /dev/null "${BASE}" 2>/dev/null; then
        log "Web installer reachable (after ${attempt} attempts)"
        break
    fi
    if [ "${attempt}" -eq 120 ]; then
        echo "[e2e] The web installer never became reachable." >&2
        exit 1
    fi
    sleep 3
done

log "Submitting configuration (deploymentTarget=generic) ..."
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

log "Creating a self-signed certificate ..."
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

log "Setting the admin group ..."
response=$(api POST /api/set-admin-group -H 'Content-Type: application/json' \
    -d "{\"admin_group\": \"${ADMIN_GROUP}\"}")
expect_ok "${response}" "set-admin-group"

log "Finishing the web installation (writes edulution.env) ..."
response=$(api POST /api/finish)
expect_ok "${response}" "finish"

log "Web installer completed successfully."
