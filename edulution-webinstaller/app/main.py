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
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from fastapi import FastAPI, Form, BackgroundTasks, Depends, Request, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ldap3 import Server, Connection, ALL, Tls
from ldap3.core.exceptions import LDAPSocketOpenError, LDAPBindError

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
from pathlib import Path


BASE_PATH = Path(__file__).parent
PAGES_PATH = BASE_PATH / "html" / "pages"

EDULUTION_DIRECTORY = os.environ.get("EDULUTION_DIRECTORY", "/srv/docker/edulution-ui")


class Token(BaseModel):
    token: str


class SSCertificate(BaseModel):
    countrycode: str
    state: str
    city: str
    organisation: str
    valid_days: int


class LECertificate(BaseModel):
    email: str


app = FastAPI()

app.mount("/css", StaticFiles(directory="css"), name="static")
app.mount("/img", StaticFiles(directory="img"), name="static")
app.mount("/js", StaticFiles(directory="js"), name="static")

with open("./html/site.html") as f:
    site = f.read()


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
        self.DATA_PROXY_USED = False
        self.DATA_DEPLOYMENT_TARGET = None
        self.DATA_INITIAL_ADMIN_GROUP = None


data = Data()


def getData():
    return data


def load_html(name: str) -> str:
    file_path = PAGES_PATH / f"{name}.html"

    if not file_path.exists():
        return f"<h2>Fehler: Datei nicht gefunden ({file_path})</h2>"

    return file_path.read_text(encoding="utf-8")


def render_page(page_name: str, **kwargs) -> str:
    html = load_html(page_name)
    for key, value in kwargs.items():
        html = html.replace(f"{{{{{key}}}}}", str(value or ""))
    return html


@app.get("/")
def root():
    html_content = load_html("01_start")
    return HTMLResponse(
        content=site.replace("##CONTENT##", html_content), status_code=200
    )


@app.get("/token")
def token():
    html_content = load_html("02_token")
    return HTMLResponse(
        content=site.replace("##CONTENT##", html_content), status_code=200
    )


@app.post("/configure")
def configure(
    targetType: str = Form(...),
    edulutionsetuptoken: str = Form(None),
    data: Data = Depends(getData),
):
    print("🔥 DEPLOYMENT TARGET =", targetType)
    data.DATA_DEPLOYMENT_TARGET = targetType

    if targetType == "generic":
        data.DATA_LMN_EXTERNAL_DOMAIN = ""
        data.DATA_LMN_BINDUSER_DN = ""
        data.DATA_LMN_BINDUSER_PW = ""
        data.DATA_LMN_LDAP_PORT = ""
        data.DATA_EDULUTION_EXTERNAL_DOMAIN = ""
    else:
        if edulutionsetuptoken:
            try:
                token_raw = base64.b64decode(edulutionsetuptoken.encode("utf-8"))
                token = json.loads(token_raw.decode("utf-8"))

                data.DATA_LMN_EXTERNAL_DOMAIN = token.get("external_domain", "")
                data.DATA_LMN_BINDUSER_DN = token.get("binduser_dn", "")
                data.DATA_LMN_BINDUSER_PW = token.get("binduser_password", "")
            except Exception as e:
                print("Token-Fehler:", e)
                data.DATA_LMN_EXTERNAL_DOMAIN = ""
                data.DATA_LMN_BINDUSER_DN = ""
                data.DATA_LMN_BINDUSER_PW = ""
        else:
            data.DATA_LMN_EXTERNAL_DOMAIN = ""
            data.DATA_LMN_BINDUSER_DN = ""
            data.DATA_LMN_BINDUSER_PW = ""

    html_content = render_page(
        "03_configure",
        DATA_LMN_EXTERNAL_DOMAIN=data.DATA_LMN_EXTERNAL_DOMAIN,
        DATA_LMN_BINDUSER_DN=data.DATA_LMN_BINDUSER_DN,
        DATA_LMN_BINDUSER_PW=data.DATA_LMN_BINDUSER_PW,
        DATA_LMN_LDAP_PORT=data.DATA_LMN_LDAP_PORT,
        DATA_EDULUTION_EXTERNAL_DOMAIN=data.DATA_EDULUTION_EXTERNAL_DOMAIN,
        DATA_DEPLOYMENT_TARGET=data.DATA_DEPLOYMENT_TARGET,
    )

    return HTMLResponse(
        content=site.replace("##CONTENT##", html_content), status_code=200
    )


@app.post("/check")
def check(
    lmn_external_domain: str = Form(None),
    lmn_binduser_dn: str = Form(None),
    lmn_binduser_pw: str = Form(None),
    lmn_ldap_schema: str = Form(None),
    lmn_ldap_port: str = Form(None),
    edulutionui_external_domain: str = Form(None),
    data: Data = Depends(getData),
):
    if (
        lmn_external_domain is not None
        and lmn_binduser_dn is not None
        and lmn_binduser_pw is not None
        and lmn_ldap_schema is not None
        and lmn_ldap_port is not None
        and edulutionui_external_domain is not None
    ):
        data.DATA_LMN_EXTERNAL_DOMAIN = lmn_external_domain
        data.DATA_LMN_BINDUSER_DN = lmn_binduser_dn
        data.DATA_LMN_BINDUSER_PW = lmn_binduser_pw
        data.DATA_LMN_LDAP_SCHEMA = lmn_ldap_schema
        data.DATA_LMN_LDAP_PORT = lmn_ldap_port
        data.DATA_EDULUTION_EXTERNAL_DOMAIN = edulutionui_external_domain
    else:
        return RedirectResponse("/")

    html_content = load_html("04_check")

    return HTMLResponse(
        content=site.replace("##CONTENT##", html_content), status_code=200
    )


@app.get("/set-admin-group")
def setAdminGroup():
    html_content = render_page(
        "06_set_admin_group",
        DATA_INITIAL_ADMIN_GROUP=data.DATA_INITIAL_ADMIN_GROUP,
    )
    return HTMLResponse(
        content=site.replace("##CONTENT##", html_content), status_code=200
    )


@app.post("/certificate")
def certificate(
    request: Request, admin_group: str = Form(None), data: Data = Depends(getData)
):
    if not data.DATA_EDULUTION_EXTERNAL_DOMAIN:
        return RedirectResponse("/")

    if admin_group:
        data.DATA_INITIAL_ADMIN_GROUP = admin_group

    proxyUsed = request.headers.get("x-forwarded-for") is not None
    data.DATA_PROXY_USED = proxyUsed

    html_content = "<h3>Zertifikat</h3><br>"

    if proxyUsed:
        html_content += """
        <div class="alert alert-warning" role="alert">
            Du verwendest einen Reverse-Proxy. Daher kann für edulution kein gültiges Zertifikat hinterlegt / ausgestellt werden.
        </div>
        <form method="GET" action="/finish">
            <button type="submit" class="login-submit-btn" id="install_button">Installation starten</button>
        </form>
        """
    else:
        html_content = render_page(
            "05_certificate",
            DATA_EDULUTION_EXTERNAL_DOMAIN=data.DATA_EDULUTION_EXTERNAL_DOMAIN,
        )

    return HTMLResponse(
        content=site.replace("##CONTENT##", html_content), status_code=200
    )


@app.post("/create-ss-certificate")
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
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, ssdata.organisation),
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


@app.post("/create-le-certificate")
def createLECertificate(ledata: LECertificate, data: Data = Depends(getData)):
    # Traefik wird jetzt Let's Encrypt selbst verwalten
    # Wir speichern nur die E-Mail für die Konfiguration
    data.DATA_LE_USED = True
    data.DATA_LE_EMAIL = ledata.email
    return {
        "status": True,
        "message": "Let's Encrypt wird beim Start von Traefik konfiguriert",
    }


@app.post("/upload-certificate")
def uplaodCertificate(cert: UploadFile = File(...), key: UploadFile = File(...)):
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


@app.post("/check-token")
def checkToken(token: Token):
    try:
        data = base64.b64decode(token.token.encode("utf-8"))
        data = json.loads(data.decode("utf-8"))
        external_domain = data["external_domain"]
        binduser_dn = data["binduser_dn"]
        binduser_pw = data["binduser_password"]
        return True
    except Exception as e:
        return False


@app.get("/check-api-status")
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


@app.get("/check-webdav-status")
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


@app.get("/check-ldap-status")
def checkLDAP(data: Data = Depends(getData)):
    try:
        if data.DATA_LMN_LDAP_SCHEMA == "ldaps":
            server = Server(
                data.DATA_LMN_EXTERNAL_DOMAIN,
                port=int(data.DATA_LMN_LDAP_PORT),
                get_info=ALL,
                connect_timeout=3,
                use_ssl=True,
                tls=Tls(validate=ssl.CERT_REQUIRED),
            )
        else:
            server = Server(
                data.DATA_LMN_EXTERNAL_DOMAIN,
                port=int(data.DATA_LMN_LDAP_PORT),
                get_info=ALL,
                connect_timeout=3,
            )
        conn = Connection(server, auto_bind=True)
        if conn.bind():
            return {"status": True, "message": "Successful"}
        return {"status": False, "message": "Keine Verbindung zum LDAP-Server!"}
    except LDAPSocketOpenError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            return {"status": False, "message": "Kein gültiges Zertifikat!"}
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}
    except Exception as e:
        print(e)
        return {"status": False, "message": "Unbekannter Fehler!"}


@app.get("/check-ldap-access-status")
def checkLDAP(data: Data = Depends(getData)):
    try:
        if data.DATA_LMN_LDAP_SCHEMA == "ldaps":
            server = Server(
                data.DATA_LMN_EXTERNAL_DOMAIN,
                port=int(data.DATA_LMN_LDAP_PORT),
                get_info=ALL,
                connect_timeout=3,
                use_ssl=True,
                tls=Tls(validate=ssl.CERT_REQUIRED),
            )
        else:
            server = Server(
                data.DATA_LMN_EXTERNAL_DOMAIN,
                port=int(data.DATA_LMN_LDAP_PORT),
                get_info=ALL,
                connect_timeout=3,
            )
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
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            return {"status": False, "message": "Kein gültiges Zertifikat!"}
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


@app.get("/finish")
def finish(background_tasks: BackgroundTasks, data: Data = Depends(getData)):
    if (
        data.DATA_LMN_EXTERNAL_DOMAIN is None
        or data.DATA_LMN_BINDUSER_DN is None
        or data.DATA_LMN_BINDUSER_PW is None
        or data.DATA_LMN_LDAP_PORT is None
        or data.DATA_LMN_LDAP_SCHEMA is None
        or data.DATA_EDULUTION_EXTERNAL_DOMAIN is None
    ):
        return RedirectResponse("/")

    background_tasks.add_task(createEdulutionEnvFile, data)

    html_content = f"""
        <h3>Konfiguration abgeschlossen</h3>
        <h2><i class="fa-solid fa-spinner fa-spin"></i></h2>
        <p>Die edulution UI wird nun installiert...</p>
        <p>Sie werden automatisch weitergeleitet, wenn die Installation abgeschlossen ist.</p>
        <script type="text/javascript">
            waitforUI();
        </script>
    """
    return HTMLResponse(
        content=site.replace("##CONTENT##", html_content), status_code=200
    )


@app.api_route("/{path_name:path}")
def catch_all():
    return RedirectResponse("/")


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

    # Let's Encrypt E-Mail hinzufügen wenn verwendet
    if data.DATA_LE_USED and data.DATA_LE_EMAIL:
        environment_file += f"\n# Let's Encrypt\n\nLE_EMAIL={data.DATA_LE_EMAIL}\n"

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

    # Docker-compose für Let's Encrypt anpassen falls nötig
    if not data.DATA_PROXY_USED and data.DATA_LE_USED:
        # docker-compose.yml anpassen um letsencrypt volume hinzuzufügen
        with open("/edulution-ui/docker-compose.yml", "r") as f:
            compose_content = f.read()

        # Füge letsencrypt volume zu edu-traefik hinzu
        # Suche nach den volumes von edu-traefik und füge die Zeile hinzu
        compose_content = compose_content.replace(
            "      - ./data/traefik/ssl:/etc/traefik/ssl\n    healthcheck:",
            "      - ./data/traefik/ssl:/etc/traefik/ssl\n      - ./data/letsencrypt:/letsencrypt\n    healthcheck:",
        )

        with open("/edulution-ui/docker-compose.yml", "w") as f:
            f.write(compose_content)

    # Traefik-Konfiguration basierend auf Proxy und Let's Encrypt anpassen
    if not data.DATA_PROXY_USED and data.DATA_LE_USED:
        # Let's Encrypt wird von Traefik verwaltet
        # Traefik.yml muss VOR docker-compose angepasst werden
        # Daher schreiben wir eine separate Datei
        traefik_le_config = f"""
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"
    http:
      tls: {{}}
  imap:
    address: ":143"

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
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web
"""

        with open("/edulution-ui/traefik.yml", "w") as f:
            f.write(traefik_le_config)

        # edulution-default.yml anpassen für Let's Encrypt
        le_config = f"""
http:
  routers:
    edulution-api:
      rule: "PathPrefix(`/edu-api`)"
      service: edulution-api
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt
        domains:
          - main: "{data.DATA_EDULUTION_EXTERNAL_DOMAIN}"
    edulution-keycloak:
      rule: "PathPrefix(`/auth`)"
      service: edulution-keycloak
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt
        domains:
          - main: "{data.DATA_EDULUTION_EXTERNAL_DOMAIN}"
    edulution-ui:
      rule: "PathPrefix(`/`)"
      service: edulution-ui
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt
        domains:
          - main: "{data.DATA_EDULUTION_EXTERNAL_DOMAIN}"

  services:
    edulution-api:
      loadBalancer:
        servers:
          - url: "http://edu-api:3000"
    edulution-ui:
      loadBalancer:
        servers:
          - url: "http://edu-ui:80"
    edulution-keycloak:
      loadBalancer:
        servers:
          - url: "http://edu-keycloak:8080"
"""
        with open("/edulution-ui/data/traefik/config/edulution-default.yml", "w") as f:
            f.write(le_config)

        # acme.json mit korrekten Berechtigungen erstellen
        os.makedirs("/edulution-ui/data/letsencrypt", exist_ok=True)
        acme_json_path = "/edulution-ui/data/letsencrypt/acme.json"
        with open(acme_json_path, "w") as f:
            f.write("{}")
        os.chmod(acme_json_path, 0o600)

    elif os.path.exists("/edulution-ui/data/traefik/ssl/cert.cert") and os.path.exists(
        "/edulution-ui/data/traefik/ssl/cert.key"
    ):
        # Selbst-signiertes oder hochgeladenes Zertifikat
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

    time.sleep(5)
    os.kill(os.getpid(), signal.SIGTERM)
