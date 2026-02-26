import base64
import json
import requests
import os
import signal
import time
import re
import secrets
import string
import ssl
import shutil
import asyncio
import threading
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from fastapi import FastAPI, Depends, Request, File, UploadFile, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import paramiko
import httpx

from ldap3 import Server, Connection, ALL, Tls
from ldap3.core.exceptions import LDAPSocketOpenError, LDAPBindError

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
from pathlib import Path


BASE_PATH = Path(__file__).parent
STATIC_PATH = BASE_PATH / "static"

EDULUTION_DIRECTORY = os.environ.get("EDULUTION_DIRECTORY", "/srv/docker/edulution-ui")


# --- Pydantic Models ---

class Token(BaseModel):
    token: str


class SSCertificate(BaseModel):
    countrycode: str
    state: str
    city: str
    organization: str
    valid_days: int


class LECertificate(BaseModel):
    email: str
    dns_provider: str


class ConfigurationRequest(BaseModel):
    organizationType: str
    deploymentTarget: str
    lmnExternalDomain: str
    lmnBinduserDn: str
    lmnBinduserPw: str
    lmnLdapSchema: str
    lmnLdapPort: int
    edulutionExternalDomain: str


class AdminGroupRequest(BaseModel):
    admin_group: str


class SSHConnection(BaseModel):
    host: str
    port: int = 22
    user: str = "root"
    password: str


class LmnConnectionCheck(BaseModel):
    host: str


# --- Bootstrap Manager (SSE with reconnect support) ---

class BootstrapManager:
    def __init__(self):
        self._events: list[dict] = []
        self._status = 'idle'  # idle, running, completed, failed
        self._condition = threading.Condition()

    @property
    def status(self):
        return self._status

    def reset(self):
        with self._condition:
            self._events = []
            self._status = 'running'
            self._condition.notify_all()

    def add_event(self, data: str, event_type: str = 'message'):
        with self._condition:
            self._events.append({
                'id': len(self._events),
                'event': event_type,
                'data': data,
            })
            self._condition.notify_all()

    def finish(self, status: str):
        with self._condition:
            self._status = status
            self._condition.notify_all()

    def stream_from(self, start_id: int):
        yield "retry: 3000\n\n"
        cursor = start_id
        while True:
            with self._condition:
                while cursor >= len(self._events) and self._status == 'running':
                    self._condition.wait(timeout=5.0)
                new_events = self._events[cursor:]
                cursor = len(self._events)
                is_done = self._status != 'running'

            for evt in new_events:
                lines = f"id: {evt['id']}\n"
                if evt['event'] != 'message':
                    lines += f"event: {evt['event']}\n"
                lines += f"data: {evt['data']}\n\n"
                yield lines

            if is_done:
                break


bootstrap_manager = BootstrapManager()


# --- Data Store ---

class Data:
    def __init__(self):
        self.DATA_LMN_EXTERNAL_DOMAIN = None
        self.DATA_LMN_BINDUSER_DN = None
        self.DATA_LMN_BINDUSER_PW = None
        self.DATA_LMN_LDAP_SCHEMA = None
        self.DATA_LMN_LDAP_PORT = None
        self.DATA_EDULUTION_EXTERNAL_DOMAIN = None
        self.DATA_LE_USED = False
        self.DATA_LE_EMAIL = None
        self.DATA_LE_DNS_PROVIDER = None
        self.DATA_LE_ACME_DNS_REGISTRATION = None
        self.DATA_PROXY_USED = False
        self.DATA_ORGANIZATION_TYPE = None
        self.DATA_DEPLOYMENT_TARGET = None
        self.DATA_INITIAL_ADMIN_GROUP = None
        self.DATA_LMN_TARGET_HOST = None


data = Data()


def getData():
    return data


# --- FastAPI App ---

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4201", "http://localhost:4301"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


# --- API Endpoints ---

@api.post("/check-token")
def checkToken(token: Token):
    try:
        decoded = base64.b64decode(token.token.encode("utf-8"))
        parsed = json.loads(decoded.decode("utf-8"))
        _ = parsed["external_domain"]
        _ = parsed["binduser_dn"]
        _ = parsed["binduser_password"]
        return True
    except Exception:
        return False


@api.post("/configure")
def configure(config: ConfigurationRequest, data: Data = Depends(getData)):
    data.DATA_ORGANIZATION_TYPE = config.organizationType
    data.DATA_DEPLOYMENT_TARGET = config.deploymentTarget
    data.DATA_LMN_EXTERNAL_DOMAIN = config.lmnExternalDomain
    data.DATA_LMN_BINDUSER_DN = config.lmnBinduserDn
    data.DATA_LMN_BINDUSER_PW = config.lmnBinduserPw
    data.DATA_LMN_LDAP_SCHEMA = config.lmnLdapSchema
    data.DATA_LMN_LDAP_PORT = config.lmnLdapPort
    data.DATA_EDULUTION_EXTERNAL_DOMAIN = config.edulutionExternalDomain
    return {"status": True, "message": "Konfiguration gespeichert"}


@api.get("/check-api-status")
def checkAPIStatus(data: Data = Depends(getData)):
    try:
        result = requests.get(
            "https://" + data.DATA_LMN_EXTERNAL_DOMAIN + ":8001",
            verify=False,
            timeout=3,
        )
        if result.status_code == 200:
            return {"status": True, "message": "Successful"}
        return {"status": False, "message": f"Got HTTP-Status {result.status_code}"}
    except requests.exceptions.ConnectTimeout:
        return {"status": False, "message": "Verbindungsfehler: Timeout!"}
    except Exception as e:
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}


@api.get("/check-webdav-status")
def checkWebDAV(data: Data = Depends(getData)):
    try:
        result = requests.get(
            "https://" + data.DATA_LMN_EXTERNAL_DOMAIN + ":443", verify=False, timeout=3
        )
        if result.status_code == 200:
            return {"status": True, "message": "Successful"}
        return {"status": False, "message": f"Got HTTP-Status {result.status_code}"}
    except requests.exceptions.ConnectTimeout:
        return {"status": False, "message": "Verbindungsfehler: Timeout!"}
    except Exception as e:
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}


def _create_ldap_server(data: Data) -> Server:
    if data.DATA_LMN_LDAP_SCHEMA == "ldaps":
        return Server(
            data.DATA_LMN_EXTERNAL_DOMAIN,
            port=int(data.DATA_LMN_LDAP_PORT),
            get_info=ALL,
            connect_timeout=3,
            use_ssl=True,
            tls=Tls(validate=ssl.CERT_NONE),
        )
    return Server(
        data.DATA_LMN_EXTERNAL_DOMAIN,
        port=int(data.DATA_LMN_LDAP_PORT),
        get_info=ALL,
        connect_timeout=3,
    )


@api.get("/check-ldap-status")
def checkLDAPStatus(data: Data = Depends(getData)):
    try:
        server = _create_ldap_server(data)
        conn = Connection(server, auto_bind=True)
        if conn.bind():
            return {"status": True, "message": "Successful"}
        return {"status": False, "message": "Keine Verbindung zum LDAP-Server!"}
    except LDAPSocketOpenError as e:
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}
    except Exception as e:
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}


@api.get("/check-ldap-access-status")
def checkLDAPAccessStatus(data: Data = Depends(getData)):
    try:
        server = _create_ldap_server(data)
        conn = Connection(
            server,
            user=data.DATA_LMN_BINDUSER_DN,
            password=data.DATA_LMN_BINDUSER_PW,
            auto_bind=True,
        )
        if conn.bind():
            return {"status": True, "message": "Successful"}
        return {"status": False, "message": "Keine Verbindung zum LDAP-Server!"}
    except LDAPSocketOpenError as e:
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}
    except LDAPBindError as e:
        if "invalidCredentials" in str(e):
            return {"status": False, "message": "LDAP Zugangsdaten falsch!"}
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}
    except Exception as e:
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}


@api.post("/set-admin-group")
def setAdminGroup(req: AdminGroupRequest, data: Data = Depends(getData)):
    data.DATA_INITIAL_ADMIN_GROUP = req.admin_group
    return {"status": True, "message": "Admin-Gruppe gespeichert"}


@api.get("/proxy-check")
def proxyCheck(request: Request):
    return {"proxyDetected": request.headers.get("x-forwarded-for") is not None}


@api.post("/create-ss-certificate")
def createSSCertificate(ssdata: SSCertificate, data: Data = Depends(getData)):
    keyfile = "/edulution-ui/data/traefik/ssl/cert.key"
    certfile = "/edulution-ui/data/traefik/ssl/cert.cert"

    try:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name(
            [
                x509.NameAttribute(
                    NameOID.COMMON_NAME, data.DATA_EDULUTION_EXTERNAL_DOMAIN
                ),
                x509.NameAttribute(NameOID.COUNTRY_NAME, ssdata.countrycode),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, ssdata.state),
                x509.NameAttribute(NameOID.LOCALITY_NAME, ssdata.city),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, ssdata.organization),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=ssdata.valid_days))
            .add_extension(
                x509.SubjectAlternativeName(
                    [x509.DNSName(data.DATA_EDULUTION_EXTERNAL_DOMAIN)]
                ),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        with open(keyfile, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        with open(certfile, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        return {"status": True, "message": "Successful"}

    except Exception as e:
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}


@api.post("/create-le-certificate")
def createLECertificate(ledata: LECertificate, data: Data = Depends(getData)):
    data.DATA_LE_USED = True
    data.DATA_LE_EMAIL = ledata.email
    data.DATA_LE_DNS_PROVIDER = ledata.dns_provider

    # Register with acme-dns
    try:
        acme_dns_url = "https://acme-dns.netzint.de/register"
        response = requests.post(acme_dns_url, timeout=15)
        if response.status_code not in (200, 201):
            return {
                "status": False,
                "message": f"ACME-DNS Registrierung fehlgeschlagen (HTTP {response.status_code})",
            }

        registration = response.json()
        data.DATA_LE_ACME_DNS_REGISTRATION = registration

        return {
            "status": True,
            "message": "Let's Encrypt wird beim Start von Traefik konfiguriert",
            "registration": registration,
        }
    except requests.exceptions.Timeout:
        return {
            "status": False,
            "message": "ACME-DNS Registrierung fehlgeschlagen: Timeout",
        }
    except Exception as e:
        print(e)
        return {
            "status": False,
            "message": f"ACME-DNS Registrierung fehlgeschlagen: {str(e)}",
        }


@api.post("/upload-certificate")
def uploadCertificate(cert: UploadFile = File(...), key: UploadFile = File(...)):
    keyfile = "/edulution-ui/data/traefik/ssl/cert.key"
    certfile = "/edulution-ui/data/traefik/ssl/cert.cert"

    try:
        with open(certfile, "wb") as buffer:
            shutil.copyfileobj(cert.file, buffer)

        with open(keyfile, "wb") as buffer:
            shutil.copyfileobj(key.file, buffer)

        return {"status": True, "message": "Successful"}

    except Exception as e:
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}


@api.post("/finish")
def finish(data: Data = Depends(getData)):
    if (
        data.DATA_LMN_EXTERNAL_DOMAIN is None
        or data.DATA_LMN_BINDUSER_DN is None
        or data.DATA_LMN_BINDUSER_PW is None
        or data.DATA_LMN_LDAP_PORT is None
        or data.DATA_LMN_LDAP_SCHEMA is None
        or data.DATA_EDULUTION_EXTERNAL_DOMAIN is None
    ):
        return {"status": False, "message": "Konfiguration unvollständig"}

    createEdulutionEnvFile(data)
    return {"status": True, "message": "Installation gestartet"}


@api.post("/shutdown")
def shutdown():
    def delayed_shutdown():
        time.sleep(2)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=delayed_shutdown, daemon=True).start()
    return {"status": True, "message": "Server wird heruntergefahren"}


# --- LMN Bootstrap & Proxy ---

BOOTSTRAP_BRANCH = os.environ.get("BOOTSTRAP_BRANCH", "main")
BOOTSTRAP_URL = f"https://raw.githubusercontent.com/edulution-io/edulution-installer/{BOOTSTRAP_BRANCH}/edulution-lmninstaller/bootstrap.sh"


@api.post("/lmn/bootstrap")
async def lmn_bootstrap(ssh: SSHConnection, data: Data = Depends(getData)):
    if bootstrap_manager.status == 'running':
        return JSONResponse(
            status_code=409,
            content={"status": False, "message": "Bootstrap läuft bereits"},
        )

    bootstrap_manager.reset()

    def run_bootstrap():
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            bootstrap_manager.add_event(f"Verbinde mit {ssh.host}:{ssh.port}...")
            client.connect(
                hostname=ssh.host,
                port=ssh.port,
                username=ssh.user,
                password=ssh.password,
                timeout=10,
            )
            bootstrap_manager.add_event("Verbindung hergestellt. Starte Bootstrap...")

            bootstrap_cmd = (
                f"tmpfile=$(mktemp) && "
                f"curl -fsSL {BOOTSTRAP_URL} -o $tmpfile && "
                f"GITHUB_BRANCH={BOOTSTRAP_BRANCH} bash $tmpfile; "
                f"rm -f $tmpfile"
            )
            if ssh.user != "root":
                command = f"sudo -S bash -c 'export GITHUB_BRANCH={BOOTSTRAP_BRANCH} && tmpfile=$(mktemp) && curl -fsSL {BOOTSTRAP_URL} -o $tmpfile && bash $tmpfile; rm -f $tmpfile'"
                bootstrap_manager.add_event("Nicht als root verbunden, verwende sudo...")
            else:
                command = bootstrap_cmd

            stdin, stdout, stderr = client.exec_command(command, get_pty=True)

            if ssh.user != "root":
                time.sleep(1)
                stdin.write(ssh.password + "\n")
                stdin.flush()

            for line in stdout:
                line_stripped = line.rstrip()
                if "[sudo]" in line_stripped and "password" in line_stripped:
                    continue
                bootstrap_manager.add_event(line_stripped)

            exit_status = stdout.channel.recv_exit_status()

            if exit_status != 0:
                for line in stderr:
                    bootstrap_manager.add_event(f"[STDERR] {line.rstrip()}")
                bootstrap_manager.add_event(
                    f"Bootstrap fehlgeschlagen (Exit-Code: {exit_status})", 'failed'
                )
                bootstrap_manager.finish('failed')
                return

            bootstrap_manager.add_event("Warte auf LMN-Installer API...")
            for attempt in range(30):
                try:
                    resp = requests.get(f"http://{ssh.host}:8000/api/health", timeout=3)
                    if resp.status_code == 200:
                        data.DATA_LMN_TARGET_HOST = ssh.host
                        bootstrap_manager.add_event("LMN-Installer API ist bereit!")
                        bootstrap_manager.add_event("Bootstrap erfolgreich", 'done')
                        bootstrap_manager.finish('completed')
                        return
                except Exception:
                    pass
                time.sleep(2)
                bootstrap_manager.add_event(f"Warte auf API... (Versuch {attempt + 1}/30)")

            bootstrap_manager.add_event("API nicht erreichbar nach Bootstrap", 'failed')
            bootstrap_manager.finish('failed')

        except paramiko.AuthenticationException:
            bootstrap_manager.add_event("SSH-Authentifizierung fehlgeschlagen", 'failed')
            bootstrap_manager.finish('failed')
        except paramiko.SSHException as e:
            bootstrap_manager.add_event(f"SSH-Fehler: {e}", 'failed')
            bootstrap_manager.finish('failed')
        except Exception as e:
            bootstrap_manager.add_event(f"Fehler: {e}", 'failed')
            bootstrap_manager.finish('failed')
        finally:
            client.close()

    threading.Thread(target=run_bootstrap, daemon=True).start()
    return {"status": True, "message": "Bootstrap gestartet"}


@api.get("/lmn/bootstrap/stream")
async def lmn_bootstrap_stream(request: Request):
    if bootstrap_manager.status == 'idle':
        return JSONResponse(
            status_code=404,
            content={"status": False, "message": "Kein Bootstrap gestartet"},
        )

    last_event_id = request.headers.get('last-event-id', '')
    start_id = int(last_event_id) + 1 if last_event_id.isdigit() else 0

    return StreamingResponse(
        bootstrap_manager.stream_from(start_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api.post("/lmn/check-connection")
def check_lmn_connection(req: LmnConnectionCheck, data: Data = Depends(getData)):
    try:
        resp = requests.get(f"http://{req.host}:8000/api/health", timeout=5)
        if resp.status_code == 200:
            data.DATA_LMN_TARGET_HOST = req.host
            return {"status": True, "message": "LMN-Server erreichbar"}
    except Exception:
        pass
    return {"status": False, "message": "LMN-Server nicht erreichbar"}


@api.api_route("/lmn/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def lmn_proxy(path: str, request: Request, data: Data = Depends(getData)):
    if not data.DATA_LMN_TARGET_HOST:
        return JSONResponse(
            status_code=503,
            content={"status": False, "message": "LMN-Server nicht verbunden. Bootstrap zuerst ausfuehren."},
        )

    target_url = f"http://{data.DATA_LMN_TARGET_HOST}:8000/api/{path}"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
                params=dict(request.query_params),
            )
            return JSONResponse(
                status_code=response.status_code,
                content=response.json(),
            )
        except httpx.ConnectError:
            return JSONResponse(
                status_code=503,
                content={"status": False, "message": "LMN-Server nicht erreichbar"},
            )
        except Exception as e:
            return JSONResponse(
                status_code=502,
                content={"status": False, "message": f"Proxy-Fehler: {e}"},
            )


# --- Register API Router ---

app.include_router(api)


# --- WebSocket Proxy (registered on app, not api router) ---

@app.websocket("/ws/lmn/{path:path}")
async def lmn_ws_proxy(websocket: WebSocket, path: str):
    if not data.DATA_LMN_TARGET_HOST:
        await websocket.close(code=1008, reason="LMN-Server nicht verbunden")
        return

    await websocket.accept()
    target_url = f"ws://{data.DATA_LMN_TARGET_HOST}:8000/ws/{path}"

    try:
        import websockets
        async with websockets.connect(target_url) as target_ws:
            async def forward_to_target():
                try:
                    while True:
                        msg = await websocket.receive_text()
                        await target_ws.send(msg)
                except (WebSocketDisconnect, Exception):
                    pass

            async def forward_to_client():
                try:
                    async for msg in target_ws:
                        await websocket.send_text(msg)
                except (WebSocketDisconnect, Exception):
                    pass

            await asyncio.gather(forward_to_target(), forward_to_client())
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# --- SPA Static File Serving ---

if STATIC_PATH.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_PATH / "assets")), name="assets")
    app.mount("/img", StaticFiles(directory=str(STATIC_PATH / "img")), name="img")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = STATIC_PATH / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_PATH / "index.html"))


# --- Helper Functions ---

def generateSecret(length=32):
    characters = string.ascii_letters + string.digits
    random_string = "".join(secrets.choice(characters) for _ in range(length))
    return random_string


def generateRandom(length=5):
    characters = string.ascii_lowercase
    random_string = "".join(secrets.choice(characters) for _ in range(length))
    return random_string


def createEdulutionEnvFile(data: Data):
    root_dn = re.search(r"(DC=.*$)", data.DATA_LMN_BINDUSER_DN).group(1)

    keycloak_eduapi_secret = generateSecret()
    keycloak_eduui_secret = generateSecret()
    keycloak_edumailcow_sync_secret = generateSecret()
    mongodb_secret = generateSecret()
    postgres_secret = generateSecret()
    keycloak_admin_secret = generateSecret()
    guacamole_mysql_root_secret = generateSecret()
    guacamole_mysql_secret = generateSecret()
    guacamole_admin_secret = generateSecret()
    onlyoffice_jwt_secret = generateSecret()
    onlyoffice_postgres_secret = generateSecret()

    mailcow_api_secret = (
        generateRandom()
        + "-"
        + generateRandom()
        + "-"
        + generateRandom()
        + "-"
        + generateRandom()
        + "-"
        + generateRandom()
    )

    realm_file = json.load(open("/edulution-ui/realm-edulution.json"))

    for client in realm_file["clients"]:
        if client["clientId"] == "edu-api":
            client["secret"] = keycloak_eduapi_secret
        if client["clientId"] == "edu-ui":
            client["secret"] = keycloak_eduui_secret
            client["rootUrl"] = "https://" + data.DATA_EDULUTION_EXTERNAL_DOMAIN + "/"
            client["adminUrl"] = "https://" + data.DATA_EDULUTION_EXTERNAL_DOMAIN + "/"
            client["redirectUris"] = [
                "https://" + data.DATA_EDULUTION_EXTERNAL_DOMAIN + "/*"
            ]
        if client["clientId"] == "edu-mailcow-sync":
            client["secret"] = keycloak_edumailcow_sync_secret

    for comp in realm_file["components"]["org.keycloak.storage.UserStorageProvider"]:
        if comp["name"] == "ldap":
            for subcomp in comp["subComponents"][
                "org.keycloak.storage.ldap.mappers.LDAPStorageMapper"
            ]:
                if subcomp["name"] == "global-groups":
                    subcomp["config"]["groups.dn"] = ["OU=Groups,OU=Global," + root_dn]
                if subcomp["name"] == "school-groups":
                    subcomp["config"]["groups.dn"] = ["OU=SCHOOLS," + root_dn]
            comp["config"]["usersDn"] = [root_dn]
            comp["config"]["bindDn"] = [data.DATA_LMN_BINDUSER_DN]
            comp["config"]["bindCredential"] = [data.DATA_LMN_BINDUSER_PW]
            comp["config"]["connectionUrl"] = [
                data.DATA_LMN_LDAP_SCHEMA
                + "://"
                + data.DATA_LMN_EXTERNAL_DOMAIN
                + ":"
                + str(data.DATA_LMN_LDAP_PORT)
            ]

    realm_file["attributes"]["frontendUrl"] = (
        "https://" + data.DATA_EDULUTION_EXTERNAL_DOMAIN + "/auth"
    )

    json.dump(realm_file, open("/edulution-ui/realm-edulution.json", "w"))

    environment_file = f"""EDULUTION_BASE_DOMAIN={data.DATA_EDULUTION_EXTERNAL_DOMAIN}

# edulution-api

EDUI_ORGANIZATION_TYPE={data.DATA_ORGANIZATION_TYPE}
EDUI_DEPLOYMENT_TARGET={data.DATA_DEPLOYMENT_TARGET}

EDUI_WEBDAV_URL=https://{data.DATA_LMN_EXTERNAL_DOMAIN}/webdav/

MONGODB_USERNAME=root
MONGODB_PASSWORD={mongodb_secret}
MONGODB_SERVER_URL=mongodb://root:{mongodb_secret}@edu-db:27017/

KEYCLOAK_EDU_UI_SECRET={keycloak_eduui_secret}
KEYCLOAK_EDU_API_CLIENT_SECRET={keycloak_eduapi_secret}

LMN_API_BASE_URL=https://{data.DATA_LMN_EXTERNAL_DOMAIN}:8001/v1/

LDAP_EDULUTION_BINDUSER_DN="{data.DATA_LMN_BINDUSER_DN}"
LDAP_EDULUTION_BINDUSER_PASSWORD="{data.DATA_LMN_BINDUSER_PW}"

EDUI_INITIAL_ADMIN_GROUP="{data.DATA_INITIAL_ADMIN_GROUP or ""}"

# edulution-db

MONGO_INITDB_ROOT_USERNAME=root
MONGO_INITDB_ROOT_PASSWORD={mongodb_secret}

# edulution-keycloak

KC_DB_USERNAME=keycloak
KC_DB_PASSWORD={postgres_secret}

KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD={keycloak_admin_secret}

# edulution-keycloak-db

POSTGRES_USER=keycloak
POSTGRES_PASSWORD={postgres_secret}

# edulution-mail

KEYCLOAK_EDU_MAILCOW_SYNC_SECRET={keycloak_edumailcow_sync_secret}
MAILCOW_API_TOKEN={mailcow_api_secret}
MAILCOW_API_URL=https://edu-traefik/sogo-mail

# edulution-guacamole

EDULUTION_GUACAMOLE_MYSQL_ROOT_PASSWORD={guacamole_mysql_root_secret}
EDULUTION_GUACAMOLE_MYSQL_PASSWORD={guacamole_mysql_secret}
EDULUTION_GUACAMOLE_ADMIN_USER=admin
EDULUTION_GUACAMOLE_ADMIN_PASSWORD={guacamole_admin_secret}

# edulution-onlyoffice

EDULUTION_ONLYOFFICE_JWT_SECRET={onlyoffice_jwt_secret}
EDULUTION_ONLYOFFICE_POSTGRES_PASSWORD={onlyoffice_postgres_secret}
"""

    # Let's Encrypt E-Mail und ACME-DNS Konfiguration hinzufügen wenn verwendet
    if data.DATA_LE_USED and data.DATA_LE_EMAIL:
        environment_file += f"\n# Let's Encrypt\n\nLE_EMAIL={data.DATA_LE_EMAIL}\n"
        environment_file += "ACME_DNS_API_BASE=https://acme-dns.netzint.de\n"
        environment_file += "ACME_DNS_STORAGE_PATH=/etc/traefik/ssl/acmedns.json\n"

    with open("/edulution-ui/edulution.env", "w") as f:
        f.write(environment_file)

    lmn_api_traefik = f"""
http:
  routers:
    linuxmuster-api:
      rule: "PathPrefix(`/api`)"
      service: linuxmuster-api
      entryPoints:
        - websecure
      tls: {{}}
      middlewares:
        - strip-api-prefix

  middlewares:
    strip-api-prefix:
      stripPrefix:
        prefixes:
          - "/api"

  services:
    linuxmuster-api:
      loadBalancer:
        servers:
          - url: "https://{data.DATA_LMN_EXTERNAL_DOMAIN}:8001"
"""

    with open("/edulution-ui/data/traefik/config/lmn-api.yml", "w") as f:
        f.write(lmn_api_traefik)

    webdav_traefik = f"""
http:
  routers:
    webdav:
      rule: "PathPrefix(`/webdav`)"
      service: webdav
      entryPoints:
        - websecure
      tls: {{}}

  services:
    webdav:
      loadBalancer:
        servers:
          - url: "https://{data.DATA_LMN_EXTERNAL_DOMAIN}/webdav"
"""

    with open("/edulution-ui/data/traefik/config/webdav.yml", "w") as f:
        f.write(webdav_traefik)

    # Traefik-Konfiguration basierend auf Proxy und Let's Encrypt anpassen
    if not data.DATA_PROXY_USED and data.DATA_LE_USED:
        # traefik.yml: Basis-Template + certificatesResolvers mit DNS-Challenge anhängen
        traefik_le_config = f"""entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: "websecure"
          scheme: "https"
  websecure:
    address: ":443"
    http:
      tls: {{}}
    transport:
      respondingTimeouts:
        readTimeout: 0s
        writeTimeout: 0s
        idleTimeout: 0s
  imap:
    address: ":143"
  imaps:
    address: ":993"

providers:
  file:
    directory: "/etc/traefik/dynamic/"
    watch: true

log:
  level: ERROR

serversTransport:
  insecureSkipVerify: true

ping: {{}}

certificatesResolvers:
  letsencrypt:
    acme:
      email: {data.DATA_LE_EMAIL}
      storage: /etc/traefik/ssl/acme.json
      dnsChallenge:
        provider: acme-dns
"""

        with open(f"{EDULUTION_DIRECTORY}/traefik.yml", "w") as f:
            f.write(traefik_le_config)

        # edulution-default.yml aus LE-Template ableiten mit Domain-Ersetzung
        le_template_path = Path(EDULUTION_DIRECTORY) / "edulution-default-le.yml"
        le_config = le_template_path.read_text().replace("{{DOMAIN}}", data.DATA_EDULUTION_EXTERNAL_DOMAIN)

        with open(f"{EDULUTION_DIRECTORY}/data/traefik/config/edulution-default.yml", "w") as f:
            f.write(le_config)

        # acme.json für ACME-Zertifikatsspeicher erstellen
        acme_json_path = f"{EDULUTION_DIRECTORY}/data/traefik/ssl/acme.json"
        with open(acme_json_path, "w") as f:
            f.write("{}")
        os.chmod(acme_json_path, 0o600)

        # acmedns.json mit Registrierungsdaten für ACME-DNS-Provider schreiben
        if data.DATA_LE_ACME_DNS_REGISTRATION:
            acmedns_data = {
                data.DATA_EDULUTION_EXTERNAL_DOMAIN: data.DATA_LE_ACME_DNS_REGISTRATION
            }
            acmedns_json_path = f"{EDULUTION_DIRECTORY}/data/traefik/ssl/acmedns.json"
            with open(acmedns_json_path, "w") as f:
                json.dump(acmedns_data, f, indent=2)

    elif os.path.exists("/edulution-ui/data/traefik/ssl/cert.cert") and os.path.exists(
        "/edulution-ui/data/traefik/ssl/cert.key"
    ):
        cert_traefik = f"""
tls:
  stores:
    default:
      defaultCertificate:
        certFile: "/etc/traefik/ssl/cert.cert"
        keyFile: "/etc/traefik/ssl/cert.key"
"""
        with open("/edulution-ui/data/traefik/config/cert.yml", "w") as f:
            f.write(cert_traefik)

    # Shutdown is now triggered explicitly via POST /api/shutdown
