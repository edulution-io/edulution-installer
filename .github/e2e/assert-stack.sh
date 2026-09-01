#!/usr/bin/env bash
#
# Verifies after the installer run that the edulution stack is actually up.

set -uo pipefail

DIRECTORY="${DIRECTORY:-/srv/docker/edulution-ui/}"
failed=0

fail() { echo "[assert] FAILED: $*" >&2; failed=1; }
ok()   { echo "[assert] ok: $*"; }

echo "=== edulution.env ==="
if [ ! -s "${DIRECTORY}edulution.env" ]; then
    fail "${DIRECTORY}edulution.env is missing or empty"
else
    ok "edulution.env present ($(wc -l <"${DIRECTORY}edulution.env") lines)"
    for key in KEYCLOAK_ADMIN KEYCLOAK_ADMIN_PASSWORD EDULUTION_BASE_DOMAIN; do
        if grep -q "^${key}=" "${DIRECTORY}edulution.env"; then
            ok "key ${key} is set"
        else
            fail "key ${key} is missing from edulution.env"
        fi
    done
fi

echo
echo "=== Downloaded templates ==="
# realm-edulution.json is removed by the installer after the Keycloak step.
for file in docker-compose.yml traefik.yml; do
    if [ ! -s "${DIRECTORY}${file}" ]; then
        fail "${file} is missing or empty"
    elif [ "$(head -c 1 "${DIRECTORY}${file}")" = "<" ]; then
        fail "${file} contains HTML instead of configuration"
    else
        ok "${file} ($(stat -c%s "${DIRECTORY}${file}") bytes)"
    fi
done
if [ ! -s "${DIRECTORY}data/traefik/config/edulution-default.yml" ]; then
    fail "data/traefik/config/edulution-default.yml is missing"
else
    ok "edulution-default.yml moved to the right place"
fi

echo
echo "=== Certificate ==="
if [ -s "${DIRECTORY}data/traefik/ssl/cert.cert" ] && [ -s "${DIRECTORY}data/traefik/ssl/cert.key" ]; then
    ok "self-signed certificate created"
else
    fail "certificate under data/traefik/ssl/ is missing"
fi

echo
echo "=== Containers ==="
docker compose --project-directory "${DIRECTORY}" ps --all --format 'table {{.Service}}\t{{.State}}\t{{.Status}}' || true
echo

service_state() {
    docker compose --project-directory "${DIRECTORY}" ps --all \
        --format '{{.Service}} {{.State}}' \
        | awk -v s="$1" '$1 == s {print $2}'
}

# These services must come up without external dependencies. `up -d` returns as
# soon as the containers are started; Mongo and Keycloak need a moment after
# that, so wait here instead of taking an immediate snapshot.
for service in edu-traefik edu-db edu-redis edu-keycloak edu-keycloak-db; do
    state=""
    for _ in $(seq 1 30); do
        state=$(service_state "${service}")
        [ "${state}" = "running" ] && break
        sleep 4
    done

    if [ -z "${state}" ]; then
        fail "service ${service} does not exist"
    elif [ "${state}" != "running" ]; then
        fail "service ${service} is '${state}' instead of 'running'"
    else
        ok "service ${service} is running"
    fi
done

# edu-ui and edu-api are only reported, on the assumption that they need a
# reachable LDAP source. They have come up healthy on a runner regardless, so
# they can be promoted to required assertions once that proves stable.
echo
echo "=== Informational only ==="
for service in edu-ui edu-api; do
    state=$(service_state "${service}")
    echo "[assert] info: ${service} = ${state:-not present}"
done

echo
echo "=== Traefik responds on 443 ==="
if curl -sS --insecure --max-time 15 -o /dev/null -w 'HTTP=%{http_code}\n' https://localhost:443/; then
    ok "traefik accepts connections on 443"
else
    fail "traefik does not respond on 443"
fi

echo
if [ "${failed}" -ne 0 ]; then
    echo "[assert] E2E failed."
    exit 1
fi
echo "[assert] All checks passed."
