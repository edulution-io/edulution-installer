# Edulution LMN Installer

Remote-Installation von [linuxmuster.net 7.3](https://docs.linuxmuster.net/de/latest/) via SSH mit einer Mini-API fuer Variablen-Konfiguration und Echtzeit-Fortschrittsueberwachung per WebSocket.

## Architektur

```
+--------------+      SSH        +--------------------------------------+
|              | -------------> |         Zielserver                    |
|    Client    |                |                                       |
|              |  curl/websocket|   bootstrap.sh                        |
|              | <------------> |     - Laedt Dateien von GitHub        |
+--------------+   Port 8000   |     - Installiert Python/pip/Ansible  |
                                |     - Startet API                     |
                                |                                       |
                                |   FastAPI Server (0.0.0.0:8000)       |
                                |     - POST /api/playbook/start        |
                                |     - GET  /api/status                |
                                |     - WS   /ws/output                 |
                                |                                       |
                                |   ansible-runner                      |
                                |     - Fuehrt Playbook lokal aus       |
                                |     - Streamt Output via WebSocket    |
                                +---------------------------------------+
```

## Schnellstart

### Voraussetzungen

- **Client** (dein Rechner): SSH-Zugang zum Zielserver, `curl`
- **Zielserver**: Ubuntu 24.04 LTS, Root-Zugang via SSH

### 1. Client-Script herunterladen und ausfuehren

```bash
curl -sSL https://raw.githubusercontent.com/hermanntoast/edulution-installer/main/install.sh -o install.sh
chmod +x install.sh
./install.sh root@10.0.0.1
```

Das Script:
1. Verbindet sich per SSH zum Zielserver
2. Laedt `bootstrap.sh` von GitHub herunter
3. Bootstrap installiert Abhaengigkeiten und laedt alle Dateien von GitHub
4. Startet die API auf Port 8000
5. Prueft ob die API bereit ist

### 2. Playbook starten

```bash
curl -X POST http://10.0.0.1:8000/api/playbook/start \
  -H "Content-Type: application/json" \
  -d '{
    "playbook": "linuxmuster.yml",
    "variables": {
      "extra_vars": {
        "lmn_schoolname": "Gymnasium Musterstadt",
        "lmn_location": "Musterstadt",
        "lmn_adminpw": "SicheresPasswort1!",
        "lmn_domainname": "linuxmuster.gymnasium-musterstadt.de"
      }
    }
  }'
```

### 3. Output live verfolgen

```bash
# Mit websocat
websocat ws://10.0.0.1:8000/ws/output

# Oder Status per REST abfragen
curl http://10.0.0.1:8000/api/status
```

### Alternative: Bootstrap direkt auf dem Zielserver

Falls kein Client-Script gewuenscht, kann der Bootstrap auch direkt auf dem Zielserver ausgefuehrt werden:

```bash
ssh root@10.0.0.1
curl -sSL https://raw.githubusercontent.com/hermanntoast/edulution-installer/main/bootstrap.sh | bash
```

## API-Referenz

### REST-Endpoints

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `GET` | `/api/health` | Health-Check |
| `GET` | `/api/status` | Aktueller Job-Status |
| `POST` | `/api/playbook/start` | Playbook starten |

### POST /api/playbook/start

**Request:**

```json
{
  "playbook": "linuxmuster.yml",
  "variables": {
    "extra_vars": {
      "lmn_schoolname": "Meine Schule",
      "lmn_adminpw": "MeinPasswort1!"
    }
  }
}
```

- `playbook`: Name der Playbook-Datei im `playbooks/`-Verzeichnis
- `variables.extra_vars`: Key-Value-Paare, die als Ansible `--extra-vars` uebergeben werden

**Response (200):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Playbook started successfully"
}
```

**Fehlercodes:**
- `409` -- Ein Playbook laeuft bereits
- `404` -- Playbook-Datei nicht gefunden
- `500` -- Interner Fehler

### GET /api/status

**Response:**

```json
{
  "status": "running",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "started_at": "2025-01-26T12:34:56.789",
  "finished_at": null,
  "return_code": null
}
```

`status` ist einer von: `idle`, `running`, `completed`, `failed`

### WebSocket /ws/output

Verbindung: `ws://<server-ip>:8000/ws/output`

Nachrichten-Format:

```json
{
  "type": "stdout",
  "data": "TASK [Erforderliche Pakete installieren] *****",
  "timestamp": "2025-01-26T12:34:56.789",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

`type` ist einer von: `stdout`, `stderr`, `event`, `status`

## Playbook-Variablen (linuxmuster.yml)

Alle Variablen haben Standardwerte und koennen via `extra_vars` ueberschrieben werden.

### Grundkonfiguration

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `lmn_server_ip` | `10.0.0.1` | IP-Adresse des Servers |
| `lmn_netmask` | `255.255.0.0` | Subnetzmaske |
| `lmn_gateway` | `10.0.0.254` | Gateway |
| `lmn_servername` | `server` | Hostname (max. 15 Zeichen, nur a-z) |
| `lmn_domainname` | `linuxmuster.lan` | Domain-Name |
| `lmn_schoolname` | `Meine Schule` | Name der Schule |
| `lmn_location` | `Musterstadt` | Ort |
| `lmn_country` | `de` | Laendercode |
| `lmn_state` | `BW` | Bundesland |
| `lmn_dhcprange` | `10.0.100.1 10.0.100.254` | DHCP-Bereich |
| `lmn_adminpw` | `Muster!` | Admin-Passwort |
| `lmn_timezone` | `Europe/Berlin` | Zeitzone |
| `lmn_locale` | `de_DE.UTF-8` | Systemsprache |

### Erweiterte Optionen

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `lmn_skip_firewall` | `true` | Kein Firewall-Setup (Firewall separat einrichten) |
| `lmn_unattended` | `true` | Keine interaktiven Abfragen |
| `lmn_disable_auto_updates` | `true` | Auto-Updates deaktivieren |
| `lmn_repo_url` | `https://deb.linuxmuster.net/` | Repository-URL |
| `lmn_repo_distribution` | `lmn73` | Repository-Distribution |

### Passwort-Anforderungen

- Mindestens 7 Zeichen
- Gross- und Kleinbuchstaben
- Mindestens eine Ziffer
- Mindestens ein Sonderzeichen: `?!+-@#%&*()[]{}`

Das Passwort wird gesetzt fuer: `root` (Server), `global-admin`, `pgmadmin`, `linbo`.

## Eigene Playbooks hinzufuegen

Lege eine neue YAML-Datei im Verzeichnis `playbooks/` ab (auf dem Zielserver unter `/opt/edulution-installer/playbooks/`). Sie wird automatisch ueber die API verfuegbar:

```bash
curl -X POST http://10.0.0.1:8000/api/playbook/start \
  -H "Content-Type: application/json" \
  -d '{"playbook": "mein-playbook.yml"}'
```

## Konfiguration

Die API laesst sich ueber Umgebungsvariablen konfigurieren:

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `EDULUTION_HOST` | `0.0.0.0` | Bind-Adresse |
| `EDULUTION_PORT` | `8000` | Port |
| `EDULUTION_PLAYBOOK_DIR` | `/opt/edulution-installer/playbooks` | Playbook-Verzeichnis |
| `EDULUTION_PRIVATE_DATA_DIR` | `/opt/edulution-installer/ansible` | Ansible-Arbeitsverzeichnis |
| `EDULUTION_SHUTDOWN_DELAY` | `5` | Sekunden bis Auto-Shutdown nach Erfolg |

## Auto-Shutdown

Die API beendet sich automatisch 5 Sekunden nach erfolgreichem Playbook-Abschluss. Das ist beabsichtigt -- der API-Server wird nur fuer die Dauer der Installation benoetigt.

## Fehlerbehebung

**API startet nicht:**
```bash
ssh root@10.0.0.1 'cat /opt/edulution-installer/api.log'
```

**Playbook laeuft schon (409):**
```bash
curl http://10.0.0.1:8000/api/status
```

**API neustarten:**
```bash
ssh root@10.0.0.1 'kill $(cat /opt/edulution-installer/api.pid); curl -sSL https://raw.githubusercontent.com/hermanntoast/edulution-installer/main/bootstrap.sh | bash'
```

## Projektstruktur

```
edulution-lmninstaller/
|-- install.sh                   # Client-Script (auf deinem Rechner)
|-- bootstrap.sh                 # Bootstrap (laedt auf dem Zielserver von GitHub)
|-- requirements.txt             # Python-Abhaengigkeiten
|-- api/
|   |-- main.py                  # FastAPI App mit Lifespan-Management
|   |-- config.py                # Konfiguration (Environment-Variablen)
|   |-- models.py                # Pydantic Request/Response Models
|   |-- routes/
|   |   |-- playbook.py          # REST-Endpoints
|   |   +-- websocket.py         # WebSocket-Endpoint
|   +-- services/
|       |-- ansible_runner.py    # Ansible-Ausfuehrung
|       +-- output_streamer.py   # WebSocket-Broadcasting
+-- playbooks/
    |-- linuxmuster.yml          # Linuxmuster.net Server Playbook
    +-- vars/
        +-- linuxmuster_vars.yml # Konfigurationsvariablen
```

## Voraussetzungen Zielserver

- Ubuntu 24.04 LTS
- Mindestens 4 GB RAM (empfohlen 16 GB)
- 25 GB System + 100 GB Daten
- Netzwerk: 10.0.0.0/16 (Standard)
- Firewall separat einrichten (wird nicht vom Playbook installiert)

## Lizenz

MIT
