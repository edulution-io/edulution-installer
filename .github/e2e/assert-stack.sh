#!/usr/bin/env bash
#
# Prueft nach dem Installer-Lauf, dass der edulution-Stack tatsaechlich steht.

set -uo pipefail

DIRECTORY="${DIRECTORY:-/srv/docker/edulution-ui/}"
failed=0

fail() { echo "[assert] FEHLER: $*" >&2; failed=1; }
ok()   { echo "[assert] ok: $*"; }

echo "=== edulution.env ==="
if [ ! -s "${DIRECTORY}edulution.env" ]; then
    fail "${DIRECTORY}edulution.env fehlt oder ist leer"
else
    ok "edulution.env vorhanden ($(wc -l <"${DIRECTORY}edulution.env") Zeilen)"
    for key in KEYCLOAK_ADMIN KEYCLOAK_ADMIN_PASSWORD EDULUTION_BASE_DOMAIN; do
        if grep -q "^${key}=" "${DIRECTORY}edulution.env"; then
            ok "Schluessel ${key} gesetzt"
        else
            fail "Schluessel ${key} fehlt in edulution.env"
        fi
    done
fi

echo
echo "=== Heruntergeladene Vorlagen ==="
# realm-edulution.json wird vom Installer nach dem Keycloak-Schritt geloescht.
for file in docker-compose.yml traefik.yml; do
    if [ ! -s "${DIRECTORY}${file}" ]; then
        fail "${file} fehlt oder ist leer"
    elif [ "$(head -c 1 "${DIRECTORY}${file}")" = "<" ]; then
        fail "${file} enthaelt HTML statt Konfiguration"
    else
        ok "${file} ($(stat -c%s "${DIRECTORY}${file}") Bytes)"
    fi
done
if [ ! -s "${DIRECTORY}data/traefik/config/edulution-default.yml" ]; then
    fail "data/traefik/config/edulution-default.yml fehlt"
else
    ok "edulution-default.yml an den richtigen Ort verschoben"
fi

echo
echo "=== Zertifikat ==="
if [ -s "${DIRECTORY}data/traefik/ssl/cert.cert" ] && [ -s "${DIRECTORY}data/traefik/ssl/cert.key" ]; then
    ok "selbstsigniertes Zertifikat erzeugt"
else
    fail "Zertifikat unter data/traefik/ssl/ fehlt"
fi

echo
echo "=== Container ==="
docker compose --project-directory "${DIRECTORY}" ps --all --format 'table {{.Service}}\t{{.State}}\t{{.Status}}' || true
echo

service_state() {
    docker compose --project-directory "${DIRECTORY}" ps --all \
        --format '{{.Service}} {{.State}}' \
        | awk -v s="$1" '$1 == s {print $2}'
}

# Diese Dienste muessen ohne externe Abhaengigkeiten hochkommen. `up -d` kehrt
# zurueck, sobald die Container gestartet sind - Mongo und Keycloak brauchen
# danach noch einen Moment, deshalb wird hier gewartet statt sofort geprueft.
for service in edu-traefik edu-db edu-redis edu-keycloak edu-keycloak-db; do
    state=""
    for _ in $(seq 1 30); do
        state=$(service_state "${service}")
        [ "${state}" = "running" ] && break
        sleep 4
    done

    if [ -z "${state}" ]; then
        fail "Dienst ${service} existiert nicht"
    elif [ "${state}" != "running" ]; then
        fail "Dienst ${service} ist '${state}' statt 'running'"
    else
        ok "Dienst ${service} laeuft"
    fi
done

# edu-ui und edu-api brauchen eine erreichbare LDAP-Quelle und einen fertig
# foederierten Keycloak. Beides gibt es im CI nicht, deshalb wird ihr Zustand
# nur berichtet und bricht den Lauf nicht ab.
echo
echo "=== Nur informativ (brauchen echtes LDAP) ==="
for service in edu-ui edu-api; do
    state=$(service_state "${service}")
    echo "[assert] info: ${service} = ${state:-nicht vorhanden}"
done

echo
echo "=== Traefik antwortet auf 443 ==="
if curl -sS --insecure --max-time 15 -o /dev/null -w 'HTTP=%{http_code}\n' https://localhost:443/; then
    ok "Traefik nimmt Verbindungen auf 443 an"
else
    fail "Traefik antwortet nicht auf 443"
fi

echo
if [ "${failed}" -ne 0 ]; then
    echo "[assert] E2E fehlgeschlagen."
    exit 1
fi
echo "[assert] Alle Pruefungen bestanden."
