# Edulution LMN Installer

Installation of [linuxmuster.net 7.3](https://docs.linuxmuster.net/de/latest/) with a minimal API for variable configuration and real-time progress monitoring via WebSocket.

## Architecture

```
+---------------------------------------+
|         Target Server                  |
|                                        |
|   curl | bash                          |
|     - Downloads files from GitHub      |
|     - Installs Python/pip/Ansible      |
|     - Starts API                       |
|                                        |
|   FastAPI Server (0.0.0.0:8000)        |
|     - POST /api/playbook/{p}/start     |
|     - GET  /api/playbook/{p}/requirements |
|     - GET  /api/status                 |
|     - WS   /ws/output                  |
|                                        |
|   ansible-runner                       |
|     - Runs playbook locally            |
|     - Streams output via WebSocket     |
+----------------------------------------+
```

## Quick Start

### Prerequisites

- **Target server**: Ubuntu 24.04 LTS, root access

### 1. Run bootstrap on the target server

```bash
curl -sSL https://raw.githubusercontent.com/edulution-io/edulution-installer/main/edulution-lmninstaller/bootstrap.sh | bash
```

The script:
1. Installs dependencies (Python, Ansible, etc.)
2. Downloads all files from GitHub
3. Sets up a Python virtual environment
4. Starts the API on port 8000

### 2. Check requirements

```bash
curl http://10.0.0.1:8000/api/playbook/linuxmuster.yml/requirements
```

### 3. Start playbook

```bash
curl -X POST http://10.0.0.1:8000/api/playbook/linuxmuster.yml/start \
  -H "Content-Type: application/json" \
  -d '{
    "variables": {
      "extra_vars": {
        "lmn_schoolname": "Gymnasium Musterstadt",
        "lmn_location": "Musterstadt",
        "lmn_adminpw": "SecurePassword1!",
        "lmn_domainname": "linuxmuster.gymnasium-musterstadt.de"
      }
    }
  }'
```

### 4. Follow output live

```bash
# With websocat
websocat ws://10.0.0.1:8000/ws/output

# Or query status via REST
curl http://10.0.0.1:8000/api/status
```

## API Reference

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/status` | Current job status |
| `GET` | `/api/playbook/{playbook}/requirements` | Check requirements |
| `POST` | `/api/playbook/{playbook}/start` | Start playbook |

### GET /api/playbook/{playbook}/requirements

Checks system requirements for a playbook. Requirements are read from `playbooks/requirements/{playbook}`.

**Example:**

```bash
curl http://localhost:8000/api/playbook/linuxmuster.yml/requirements
```

**Response (200):**

```json
{
  "playbook": "linuxmuster.yml",
  "all_passed": true,
  "checks": [
    {
      "name": "os_distribution",
      "status": "passed",
      "required": "Ubuntu",
      "actual": "Ubuntu",
      "message": "OS distribution is Ubuntu"
    },
    {
      "name": "ram",
      "status": "passed",
      "required": ">= 4 GB",
      "actual": "15.5 GB",
      "message": "RAM 15.5 GB meets minimum 4 GB"
    }
  ],
  "system_info": {
    "os": "Ubuntu",
    "os_version": "24.04",
    "ram_gb": 15.5,
    "disks": [
      {"name": "sda", "size_gb": 100.0},
      {"name": "sdb", "size_gb": 500.0}
    ]
  }
}
```

Always returns `200`. If no requirements file exists, `all_passed` is `true` with a `skipped` check.

`checks[].status` is one of: `passed`, `failed`, `skipped`

### POST /api/playbook/{playbook}/start

Starts a playbook. The playbook name is passed as a path parameter.

**Request:**

```json
{
  "variables": {
    "extra_vars": {
      "lmn_schoolname": "My School",
      "lmn_adminpw": "MyPassword1!"
    }
  }
}
```

- `variables.extra_vars`: Key-value pairs passed as Ansible `--extra-vars`

**Example:**

```bash
curl -X POST http://localhost:8000/api/playbook/linuxmuster.yml/start \
  -H "Content-Type: application/json" \
  -d '{"variables": {"extra_vars": {"lmn_adminpw": "MyPassword1!"}}}'
```

**Response (200):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Playbook started successfully"
}
```

**Error codes:**
- `409` -- A playbook is already running
- `404` -- Playbook file not found
- `500` -- Internal error

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

`status` is one of: `idle`, `running`, `completed`, `failed`

### WebSocket /ws/output

Connection: `ws://<server-ip>:8000/ws/output`

Message format:

```json
{
  "type": "stdout",
  "data": "TASK [Install required packages] *****",
  "timestamp": "2025-01-26T12:34:56.789",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

`type` is one of: `stdout`, `stderr`, `event`, `status`

## Playbook Variables (linuxmuster.yml)

All variables have default values. Through the API, the settings in the tables below can be passed as `extra_vars`; repository and download settings always come from the playbook.

### Basic Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `lmn_server_ip` | `10.0.0.1` | Server IP address |
| `lmn_netmask` | `255.255.0.0` | Subnet mask |
| `lmn_gateway` | `10.0.0.254` | Gateway |
| `lmn_servername` | `server` | Hostname (max 15 chars, a-z only) |
| `lmn_domainname` | `linuxmuster.lan` | Domain name |
| `lmn_schoolname` | `Meine Schule` | School name |
| `lmn_location` | `Musterstadt` | Location |
| `lmn_country` | `de` | Country code |
| `lmn_state` | `BW` | State/province |
| `lmn_dhcprange` | `10.0.100.1 10.0.100.254` | DHCP range |
| `lmn_adminpw` | `Muster!` | Admin password; has to be set, the default is refused |
| `lmn_timezone` | `Europe/Berlin` | Timezone |
| `lmn_locale` | `de_DE.UTF-8` | System locale |

### Advanced Options

| Variable | Default | Description |
|----------|---------|-------------|
| `lmn_skip_firewall` | `true` | Skip firewall setup (configure firewall separately) |
| `lmn_unattended` | `true` | No interactive prompts |
| `lmn_disable_auto_updates` | `true` | Disable auto updates |

### Data Disk

| Variable | Default | Description |
|----------|---------|-------------|
| `lmn_setup_data_disk` | `true` | Set up a separate data disk |
| `lmn_data_disk` | `''` | Device such as `/dev/vdb`; empty means the first empty non-system disk |
| `lmn_lvm_volumes` | `''` | Volume sizes such as `var:10,linbo:40,global:10,default-school:100%FREE`; empty means the lmn-prepare default |

### Network Services

| Variable | Default | Description |
|----------|---------|-------------|
| `lmn_dns_forwarder` | `auto` | DNS forwarder for Samba; `auto` takes the host's resolver |

### Installation next to edulution

| Variable | Default | Description |
|----------|---------|-------------|
| `lmn_local_install` | `false` | linuxmuster runs on the same machine as edulution |
| `lmn_webui_port` | `8443` | Port of the linuxmuster web UI in that case |

The API checks every value against the form its setting needs (addresses, names, disk, port, flags). Server name, domain name and country are taken in lower case. School name, location and state may contain any text except line breaks, control characters, `%` and `$`; the admin password uses the characters the web installer allows.

### Password Requirements

- At least 7 characters
- Upper and lower case letters
- At least one digit
- At least one special character: `?!+-@#%&*()[]{}`

The password is set for: `root` (server), `global-admin`, `pgmadmin`, `linbo`.

## Adding Custom Playbooks

Place a new YAML file in the `playbooks/` directory (on the target server at `/opt/edulution-installer/playbooks/`). It becomes automatically available via the API; through the API it receives only the settings listed under Playbook Variables (`ALLOWED_EXTRA_VARS` in `api/models.py`):

```bash
curl -X POST http://10.0.0.1:8000/api/playbook/my-playbook.yml/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

Optionally, requirements can be defined in `playbooks/requirements/my-playbook.yml` and checked via `GET /api/playbook/my-playbook.yml/requirements`.

## Configuration

The API can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `EDULUTION_HOST` | `0.0.0.0` | Bind address |
| `EDULUTION_PORT` | `8000` | Port |
| `EDULUTION_PLAYBOOK_DIR` | `/opt/edulution-installer/playbooks` | Playbook directory |
| `EDULUTION_PRIVATE_DATA_DIR` | `/opt/edulution-installer/ansible` | Ansible working directory |
| `EDULUTION_SHUTDOWN_DELAY` | `5` | Seconds until auto-shutdown after success |

## Auto-Shutdown

The API automatically shuts down 5 seconds after a successful playbook run. This is intentional -- the API server is only needed for the duration of the installation.

## Troubleshooting

**API won't start:**
```bash
cat /opt/edulution-installer/api.log
```

**Playbook already running (409):**
```bash
curl http://localhost:8000/api/status
```

**Restart the API:**
```bash
kill $(cat /opt/edulution-installer/api.pid)
curl -sSL https://raw.githubusercontent.com/edulution-io/edulution-installer/main/edulution-lmninstaller/bootstrap.sh | bash
```

## Project Structure

```
edulution-lmninstaller/
|-- bootstrap.sh                 # Bootstrap (downloads from GitHub on target server)
|-- requirements.txt             # Python dependencies
|-- api/
|   |-- main.py                  # FastAPI app with lifespan management
|   |-- config.py                # Configuration (environment variables)
|   |-- models.py                # Pydantic request/response models
|   |-- routes/
|   |   |-- playbook.py          # REST endpoints
|   |   +-- websocket.py         # WebSocket endpoint
|   +-- services/
|       |-- ansible_runner.py    # Ansible execution
|       |-- output_streamer.py   # WebSocket broadcasting
|       +-- system_checker.py    # Requirements checking
+-- playbooks/
    |-- linuxmuster.yml          # linuxmuster.net server playbook
    +-- requirements/
        +-- linuxmuster.yml      # System requirements
```

## Target Server Requirements

- Ubuntu 24.04 LTS
- At least 4 GB RAM (16 GB recommended)
- 25 GB system + 100 GB data
- Network: 10.0.0.0/16 (default)
- Firewall must be configured separately (not installed by the playbook)
