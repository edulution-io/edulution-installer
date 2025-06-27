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
import subprocess
import shutil
import yaml

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

data = Data()

def getData():
    return data

EDULUTION_DIRECTORY = os.environ.get("EDULUTION_DIRECTORY", "/srv/docker/edulution-ui")

@app.get("/")
def root():
    html_content = """
    <h1>Herzlich Willkommen!</h1>
    <form method="GET" action="/token">
    <br><br>
    <input type="submit" class="gradient-button" value="Installation starten" id="btn_configure"></input>
    </form>
    """

    return HTMLResponse(content=site.replace("##CONTENT##", html_content), status_code=200)


@app.get("/token")
def token():
    html_content = """
    <form method="POST" action="/configure">
        <div class="form-group">
            <p>Füge hier deinen "Edulution-Setup-Token" ein:</p>
            <textarea class="form-control" rows="5" name="edulutionsetuptoken" id="edulutionsetuptoken" oninput="checkToken()" onfocus="checkToken()"></textarea>
        </div>
        <input type="submit" class="gradient-button" value="Überprüfen" id="btn_install" disabled></input>
        <br>
        <hr>
        <br>
        <p>oder gebe die Daten manuell ein:</p>
        <input type="submit" class="gradient-button" value="Manuell eingeben"></input>
    </form>
    """
    return HTMLResponse(content=site.replace("##CONTENT##", html_content), status_code=200)

@app.post("/configure")
def configure(edulutionsetuptoken: str = Form(None), data: Data = Depends(getData)):
    if edulutionsetuptoken is not None and edulutionsetuptoken != "":
        token = base64.b64decode(edulutionsetuptoken.encode("utf-8"))
        token = json.loads(token.decode("utf-8"))

        data.DATA_LMN_EXTERNAL_DOMAIN = token["external_domain"]
        data.DATA_LMN_BINDUSER_DN = token["binduser_dn"]
        data.DATA_LMN_BINDUSER_PW = token["binduser_password"]
    else:
        data.DATA_LMN_EXTERNAL_DOMAIN = ""
        data.DATA_LMN_BINDUSER_DN = ""
        data.DATA_LMN_BINDUSER_PW = ""

    html_content = f"""
    <form method="POST" action="/check">
        <div class="form-group">
            <p>Externe Domain des Linuxmuster-Servers:</p>
            <input type="text" class="form-control" oninput="checkInput()" name="lmn_external_domain" id="lmn_external_domain" value="{data.DATA_LMN_EXTERNAL_DOMAIN}" required />
        </div>
        <div class="form-group">
            <p>LDAP Benutzer:</p>
            <input type="text" class="form-control" oninput="checkInput()" name="lmn_binduser_dn" id="lmn_binduser_dn" value="{data.DATA_LMN_BINDUSER_DN}" required />
        </div>
        <div class="form-group">
            <p>LDAP Passwort:</p>
            <input type="text" class="form-control" oninput="checkInput()" name="lmn_binduser_pw" id="lmn_binduser_pw" value="{data.DATA_LMN_BINDUSER_PW}" required />
        </div>
        <div class="row">
            <div class="col-md form-group">
                <p>LDAP-Schema:</p>
                <select class="form-select" name="lmn_ldap_schema" id="lmn_ldap_schema" oninput="checkInput()">
                    <option value="ldap">ldap://</option>
                    <option value="ldaps" selected>ldaps://</option>
                </select>
            </div>
            <div class="col-md form-group"> 
                <p>LDAP-Port:</p>
                <input type="number" class="form-control" oninput="checkInput()" name="lmn_ldap_port" id="lmn_ldap_port" min="1" max="65535" value="636" required />
            </div>  
        </div>
        <div class="form-group">
            <p>Externe Domain der edulutionUI:</p>
            <input type="text" class="form-control" oninput="checkInput()" name="edulutionui_external_domain" id="edulutionui_external_domain" required />
        </div>
        <input type="submit" class="gradient-button" value="Überprüfen" id="btn_install" disabled></input>
    </form>
    <script>loadDomain();checkInput();</script>
    """
    return HTMLResponse(content=site.replace("##CONTENT##", html_content), status_code=200)

@app.post("/check")
def check(lmn_external_domain: str = Form(None), lmn_binduser_dn: str = Form(None), lmn_binduser_pw: str = Form(None), lmn_ldap_schema: str = Form(None), lmn_ldap_port: str = Form(None), edulutionui_external_domain: str = Form(None), data: Data = Depends(getData)):
    if lmn_external_domain is not None and lmn_binduser_dn is not None and lmn_binduser_pw is not None and lmn_ldap_schema is not None and lmn_ldap_port is not None and edulutionui_external_domain is not None:
        data.DATA_LMN_EXTERNAL_DOMAIN = lmn_external_domain
        data.DATA_LMN_BINDUSER_DN = lmn_binduser_dn
        data.DATA_LMN_BINDUSER_PW = lmn_binduser_pw
        data.DATA_LMN_LDAP_SCHEMA = lmn_ldap_schema
        data.DATA_LMN_LDAP_PORT = lmn_ldap_port
        data.DATA_EDULUTION_EXTERNAL_DOMAIN = edulutionui_external_domain
    else:
        return RedirectResponse("/")
    
    html_content = f"""
    <h3>Überprüfung der Abhängigkeiten</h3>
    <br>
    <div class="card text-bg-dark">
        <div class="card-body">
            <div class="card-icon" id="api_status">
                <i class="fa-solid fa-spinner fa-spin"></i>
            </div>
            <div class="card-text">Überprüfung der Linuxmuster-API</div>
            <div class="card-button">
                <button type="button" class="btn btn-secondary" onclick="checkAPIStatus()" id="api_status_retry">Erneut prüfen</button>
            </div>
        </div>
    </div>
    <div class="card text-bg-dark">
        <div class="card-body">
            <div class="card-icon" id="webdav_status">
                <i class="fa-solid fa-spinner fa-spin"></i>
            </div>
            <div class="card-text">Überprüfung des WebDAV-Servers</div>
            <div class="card-button">
                <button type="button" class="btn btn-secondary" onclick="checkWebDAVStatus()" id="webdav_status_retry">Erneut prüfen</button>
            </div>
        </div>
    </div>
    <div class="card text-bg-dark">
        <div class="card-body">
            <div class="card-icon" id="ldap_status">
                <i class="fa-solid fa-spinner fa-spin"></i>         
            </div>
            <div class="card-text">Überprüfung des LDAP(s)-Servers</div>
            <div class="card-button">
                <button type="button" class="btn btn-secondary" onclick="checkLDAPStatus()" id="ldap_status_retry">Erneut prüfen</button>
            </div>
        </div>
    </div>
    <div class="card text-bg-dark">
        <div class="card-body">
            <div class="card-icon" id="ldap-access_status">
                <i class="fa-solid fa-spinner fa-spin"></i>
            </div>
            <div class="card-text">Überprüfung der LDAP(s) Zugangsdaten</div>
            <div class="card-button">
                <button type="button" class="btn btn-secondary" onclick="checkLDAPAccessStatus()" id="ldap-access_status_retry">Erneut prüfen</button>
            </div>
        </div>
    </div>
    <form method="GET" action="/certificate">
        <input type="submit" class="gradient-button" value="Weiter" id="cert_button" disabled></input>
    </form>
    <form method="GET" action="/configure">
        <input type="submit" class="gradient-button" value="Zurück"></input>
    </form>
    <script type="text/javascript">
        checkAll();
    </script>
    """

    return HTMLResponse(content=site.replace("##CONTENT##", html_content), status_code=200)

@app.get("/certificate")
def certificate(request: Request, data: Data = Depends(getData)):
    if not data.DATA_EDULUTION_EXTERNAL_DOMAIN:
        return RedirectResponse("/")
    
    proxyUsed = request.headers.get("x-forwarded-for") is not None
    
    html_content = "<h3>Zertifikat</h3><br>"

    if proxyUsed:
        html_content += """
        <div class="alert alert-warning" role="alert">
            Du verwendest einen Reverse-Proxy. Daher kann für edulution kein gültiges Zertifikat hinterlegt / ausgestellt werden.
        </div>
        <form method="GET" action="/finish">
            <input type="submit" class="gradient-button" value="Installation starten" id="install_button"></input>
        </form>
        """
    else:
        html_content += f"""
        <div class="alert alert-success" role="alert">
            Du verwendest keinen Reverse-Proxy. Für edulution benötigst du ein Zertifikat, welches du hier generieren, erstellen oder hochladen kannst.
        </div>
        <div class="form-check certificate_radio">
            <input class="form-check-input" type="radio" onchange="loadCertificateContent(this);checkCertificateInput()" name="certificate_type" id="certificate_type_1" value="1">
            <label class="form-check-label" for="certificate_type_1">
                Selbst-Signiertes-Zertifikat generieren
            </label>
        </div>
        <div id="content_1" class="certificate_content">
            <div class="row">
                <div class="col-md-3 certificate_label">
                    Domain:
                </div>
                <div class="col-md-9">
                    <input type="text" class="form-control" oninput="checkCertificateInput()" name="cert_domain" id="cert_domain" value="{data.DATA_EDULUTION_EXTERNAL_DOMAIN}" readonly/>
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label">
                    Ländercode (DE):
                </div>
                <div class="col-md-9">
                    <input type="text" class="form-control" oninput="checkCertificateInput()" name="cert_country_code" id="cert_country_code" />
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label">
                    Bundesland:
                </div>
                <div class="col-md-9">
                    <input type="text" class="form-control" oninput="checkCertificateInput()" name="cert_state" id="cert_state" />
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label">
                    Stadt:
                </div>
                <div class="col-md-9">
                    <input type="text" class="form-control" oninput="checkCertificateInput()" name="cert_city" id="cert_city" />
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label">
                    Organisation:
                </div>
                <div class="col-md-9">
                    <input type="text" class="form-control" oninput="checkCertificateInput()" name="cert_organisation" id="cert_organisation" />
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label">
                    Gültigkeitsdauer (Tage):
                </div>
                <div class="col-md-9">
                    <input type="number" class="form-control" oninput="checkCertificateInput()" name="cert_valid_days" id="cert_valid_days" />
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label"></div>
                <div class="col-auto" style="text-align: left;">
                    <button class="gradient-button" style="padding: 10px 15px;margin-top:0px;" id="cert_generate_btn" onclick="generateSSCertificate()" disabled>Zertifikat generieren</button>
                </div>
                <div class="col-auto" style="text-align: left;">
                    <div class="card-icon" id="ss_certificate_status">
                    </div>
                </div>
            </div>
        </div>
        <div class="form-check certificate_radio">
            <input class="form-check-input" type="radio" onchange="loadCertificateContent(this);checkLECertificateInput();" name="certificate_type" id="certificate_type_2" value="2">
            <label class="form-check-label" for="certificate_type_2">
                Zertifikat mit Let's Encrypt erstellen
            </label>
        </div>
        <div id="content_2" class="certificate_content">
            <div class="row">
                <div class="col-md-3 certificate_label">
                    Domain:
                </div>
                <div class="col-md-9">
                    <input type="text" class="form-control" oninput="checkLECertificateInput()" name="cert_domain" id="lecert_domain" value="{data.DATA_EDULUTION_EXTERNAL_DOMAIN}" readonly/>
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label">
                    E-Mail-Adresse:
                </div>
                <div class="col-md-9">
                    <input type="email" class="form-control" oninput="checkLECertificateInput()" name="cert_email" id="lecert_email" />
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label"></div>
                <div class="col-auto" style="text-align: left;">
                    <button class="gradient-button" style="padding: 10px 15px;margin-top:0px;"  id="lecert_create_btn" onclick="createLECertificate()" disabled>Zertifikat erstellen</button>
                </div>
                <div class="col-auto" style="text-align: left;">
                    <div class="card-icon" id="le_certificate_status">
                    </div>
                </div>
            </div>
        </div>
        <div class="form-check certificate_radio">
            <input class="form-check-input" type="radio" onchange="loadCertificateContent(this)" name="certificate_type" id="certificate_type_3" value="3" checked>
            <label class="form-check-label" for="certificate_type_3">
                Zertifikat hochladen
            </label>
        </div>
        <div id="content_3" class="certificate_content" style="display: block;">
            <div class="row">
                <div class="col-md-3 certificate_label">
                    Zertifikats-Datei:
                </div>
                <div class="col-md-9">
                    <input type="file" class="form-control" oninput="checkUploadCertificateInput()" name="certificate_file" id="certificate_file" accept=".crt,.pem,.cer,.cert" />
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label">
                    Zertifikats-Key:
                </div>
                <div class="col-md-9">
                    <input type="file" class="form-control" oninput="checkUploadCertificateInput()" name="key_file" id="key_file" accept=".key,.pem" />
                </div>
            </div>
            <div class="row">
                <div class="col-md-3 certificate_label"></div>
                <div class="col-auto" style="text-align: left;">
                    <button class="gradient-button" style="padding: 10px 15px;margin-top:0px;"  id="cert_upload_btn" onclick="uploadCertificate()" disabled>Dateien hochladen</button>
                </div>
                <div class="col-auto" style="text-align: left;">
                    <div class="card-icon" id="upload_certificate_status">
                    </div>
                </div>
            </div>
        </div>
        <form method="GET" action="/finish">
            <input type="submit" class="gradient-button" value="Installation starten" id="install_button" disabled></input>
        </form>
        """
    
    return HTMLResponse(content=site.replace("##CONTENT##", html_content), status_code=200)

@app.post("/create-ss-certificate")
def createSSCertificate(ssdata: SSCertificate, data: Data = Depends(getData)):
    keyfile = "/edulution-ui/data/traefik/ssl/cert.key"
    certfile = "/edulution-ui/data/traefik/ssl/cert.cert"

    try:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, data.DATA_EDULUTION_EXTERNAL_DOMAIN),
            x509.NameAttribute(NameOID.COUNTRY_NAME, ssdata.countrycode),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, ssdata.state),
            x509.NameAttribute(NameOID.LOCALITY_NAME, ssdata.city),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, ssdata.organisation),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=ssdata.valid_days))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(data.DATA_EDULUTION_EXTERNAL_DOMAIN)]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        with open(keyfile, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(certfile, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        return { "status": True, "message": "Successful" }

    except Exception as e:
        print(e)
        return { "status": False, "message": "Unbekannter Fehler!" }

@app.post("/create-le-certificate")
def createSSCertificate(ledata: LECertificate, data: Data = Depends(getData)):
    keyfile = "/edulution-ui/data/traefik/ssl/cert.key"
    certfile = "/edulution-ui/data/traefik/ssl/cert.cert"

    command = [
        "docker", "run", "--rm",
        "-p", "80:80",
        "-v", f"{EDULUTION_DIRECTORY}/data/certbot/etc:/etc/letsencrypt",
        "-v", f"{EDULUTION_DIRECTORY}/data/certbot/var:/var/lib/letsencrypt",
        "certbot/certbot",
        "certonly",
        "--standalone",
        "-d", data.DATA_EDULUTION_EXTERNAL_DOMAIN,
        "--agree-tos",
        "--no-eff-email",
        "--email", ledata.email
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)

    if result.returncode == 0 and "Successfully received certificate" in result.stdout:
        if os.path.exists(f"/edulution-ui/data/certbot/etc/live/{data.DATA_EDULUTION_EXTERNAL_DOMAIN}/fullchain.pem") and os.path.exists(f"/edulution-ui/data/certbot/etc/live/{data.DATA_EDULUTION_EXTERNAL_DOMAIN}/privkey.pem"):
            if os.path.exists(certfile):
                os.remove(certfile)
            if os.path.exists(keyfile):
                os.remove(keyfile)
            shutil.copy2(f"/edulution-ui/data/certbot/etc/live/{data.DATA_EDULUTION_EXTERNAL_DOMAIN}/fullchain.pem", certfile)
            shutil.copy2(f"/edulution-ui/data/certbot/etc/live/{data.DATA_EDULUTION_EXTERNAL_DOMAIN}/privkey.pem", keyfile)
            data.DATA_LE_USED = True
            return { "status": True, "message": "Successful" }
        else:
            return { "status": False, "message": "Zertifikat wurde nicht erstellt!" }
    else:
        if "too many certificates" in result.stderr:
            return { "status": False, "message": "Es wurden zu viele Zertifikate angefragt!" }
        return { "status": False, "message": "Unbekannter Fehler!" }

@app.post("/upload-certificate")
def createSSCertificate(cert: UploadFile = File(...), key: UploadFile = File(...)):
    keyfile = "/edulution-ui/data/traefik/ssl/cert.key"
    certfile = "/edulution-ui/data/traefik/ssl/cert.cert"

    try:
        with open(certfile, "wb") as buffer:
            shutil.copyfileobj(cert.file, buffer)

        with open(keyfile, "wb") as buffer:
            shutil.copyfileobj(key.file, buffer)

        return { "status": True, "message": "Successful" }
        
    except Exception as e:
        print(e)
        return { "status": False, "message": "Unbekannter Fehler!" }

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
        result = requests.get("https://" + data.DATA_LMN_EXTERNAL_DOMAIN + ":8001", verify=False, timeout=3)
        if result.status_code == 200:
            return { "status": True, "message": "Successful" }
        return { "status": False, "message": f"Got HTTP-Status {result.status_code}" }
    except requests.exceptions.ConnectTimeout:
        return { "status": False, "message": "Verbindungsfehler: Timeout!" }
    except Exception as e:
        print(e)
        return { "status": False, "message": "Unbekannter Fehler!" }
    
@app.get("/check-webdav-status")
def checkWebDAV(data: Data = Depends(getData)):
    try:
        result = requests.get("https://" + data.DATA_LMN_EXTERNAL_DOMAIN + ":443", verify=False, timeout=3)
        if result.status_code == 200:
            return { "status": True, "message": "Successful" }
        return { "status": False, "message": f"Got HTTP-Status {result.status_code}" }
    except requests.exceptions.ConnectTimeout:
        return { "status": False, "message": "Verbindungsfehler: Timeout!" }
    except Exception as e:
        print(e)
        return { "status": False, "message": "Unbekannter Fehler!" }
    
@app.get("/check-ldap-status")
def checkLDAP(data: Data = Depends(getData)):
    try:
        if data.DATA_LMN_LDAP_SCHEMA == "ldaps":
            server = Server(data.DATA_LMN_EXTERNAL_DOMAIN, port=int(data.DATA_LMN_LDAP_PORT), get_info=ALL, connect_timeout=3, use_ssl=True, tls=Tls(validate=ssl.CERT_REQUIRED))
        else:
            server = Server(data.DATA_LMN_EXTERNAL_DOMAIN, port=int(data.DATA_LMN_LDAP_PORT), get_info=ALL, connect_timeout=3)
        conn = Connection(server, auto_bind=True)
        if conn.bind():
            return { "status": True, "message": "Successful" }
        return { "status": False, "message": "Keine Verbindung zum LDAP-Server!" }
    except LDAPSocketOpenError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            return { "status": False, "message": "Kein gültiges Zertifikat!" }
        print(e)
        return { "status": False, "message": "Unbekannter Fehler!" }
    except Exception as e:
        print(e)
        return { "status": False, "message": "Unbekannter Fehler!" }
    
@app.get("/check-ldap-access-status")
def checkLDAP(data: Data = Depends(getData)):
    try:
        if data.DATA_LMN_LDAP_SCHEMA == "ldaps":
            server = Server(data.DATA_LMN_EXTERNAL_DOMAIN, port=int(data.DATA_LMN_LDAP_PORT), get_info=ALL, connect_timeout=3, use_ssl=True, tls=Tls(validate=ssl.CERT_REQUIRED))
        else:
            server = Server(data.DATA_LMN_EXTERNAL_DOMAIN, port=int(data.DATA_LMN_LDAP_PORT), get_info=ALL, connect_timeout=3)
        conn = Connection(server, user=data.DATA_LMN_BINDUSER_DN, password=data.DATA_LMN_BINDUSER_PW, auto_bind=True)
        if conn.bind():
            return { "status": True, "message": "Successful" }
        return { "status": False, "message": "Keine Verbindung zum LDAP-Server!" }
    except LDAPSocketOpenError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            return { "status": False, "message": "Kein gültiges Zertifikat!" }
        print(e)
        return { "status": False, "message": "Unbekannter Fehler!" }
    except LDAPBindError as e:
        if "invalidCredentials" in str(e):
            return { "status": False, "message": "LDAP Zugangsdaten falsch!" }
        print(e)
        return { "status": False, "message": "Unbekannter Fehler!" }
    except Exception as e:
        print(e)
        return { "status": False, "message": "Unbekannter Fehler!" }

@app.get("/finish")
def finish(background_tasks: BackgroundTasks, data: Data = Depends(getData)):
    if data.DATA_LMN_EXTERNAL_DOMAIN is None or data.DATA_LMN_BINDUSER_DN is None or data.DATA_LMN_BINDUSER_PW is None or data.DATA_LMN_LDAP_PORT is None or data.DATA_LMN_LDAP_SCHEMA is None or data.DATA_EDULUTION_EXTERNAL_DOMAIN is None:
        return RedirectResponse("/")
    
    background_tasks.add_task(createEdulutionEnvFile, data)

    html_content = f"""
        <h3>Konfiguration abgeschlossen</h3>
        <h2><i class="fa-solid fa-spinner fa-spin"></i></h2>
        <p>Die edulutionUI wird nun installiert...</p>
        <p>Sie werden automatisch weitergeleitet, wenn die Installation abgeschlossen ist.</p>
        <script type="text/javascript">
            waitforUI();
        </script>
    """
    return HTMLResponse(content=site.replace("##CONTENT##", html_content), status_code=200)

@app.api_route("/{path_name:path}")
def catch_all():
    return RedirectResponse("/")

def generateSecret(length=32):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string

def generateRandom(length=5):
    characters = string.ascii_lowercase
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
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

    mailcow_api_secret = generateRandom() + "-" + generateRandom() + "-" + generateRandom() + "-" + generateRandom() + "-" + generateRandom()

    realm_file = json.load(open("/edulution-ui/realm-edulution.json"))

    for client in realm_file["clients"]:
        if client["clientId"] == "edu-api":
            client["secret"] = keycloak_eduapi_secret
        if client["clientId"] == "edu-ui":
            client["secret"] = keycloak_eduui_secret
            client["rootUrl"] = "https://" + data.DATA_EDULUTION_EXTERNAL_DOMAIN + "/"
            client["adminUrl"] = "https://" + data.DATA_EDULUTION_EXTERNAL_DOMAIN + "/"
            client["redirectUris"] = [ "https://" + data.DATA_EDULUTION_EXTERNAL_DOMAIN + "/*" ]
        if client["clientId"] == "edu-mailcow-sync":
            client["secret"] = keycloak_edumailcow_sync_secret

    for comp in realm_file["components"]["org.keycloak.storage.UserStorageProvider"]:
        if comp["name"] == "ldap":
            for subcomp in comp["subComponents"]["org.keycloak.storage.ldap.mappers.LDAPStorageMapper"]:
                if subcomp["name"] == "global-groups":
                    subcomp["config"]["groups.dn"] = [ "OU=Groups,OU=Global," + root_dn ]
                if subcomp["name"] == "school-groups":
                    subcomp["config"]["groups.dn"] = [ "OU=SCHOOLS," + root_dn ]
            comp["config"]["usersDn"] = [ root_dn ]
            comp["config"]["bindDn"] = [ data.DATA_LMN_BINDUSER_DN ]
            comp["config"]["bindCredential"] = [ data.DATA_LMN_BINDUSER_PW ]
            comp["config"]["connectionUrl"] = [ data.DATA_LMN_LDAP_SCHEMA + "://" + data.DATA_LMN_EXTERNAL_DOMAIN + ":" + str(data.DATA_LMN_LDAP_PORT) ]

    realm_file["attributes"]["frontendUrl"] = "https://" + data.DATA_EDULUTION_EXTERNAL_DOMAIN + "/auth"

    json.dump(realm_file, open("/edulution-ui/realm-edulution.json", "w"))

    environment_file = f"""EDULUTION_BASE_DOMAIN={data.DATA_EDULUTION_EXTERNAL_DOMAIN}
    
# edulution-api

EDUI_WEBDAV_URL=https://{data.DATA_LMN_EXTERNAL_DOMAIN}/webdav/

MONGODB_USERNAME=root
MONGODB_PASSWORD={mongodb_secret}
MONGODB_SERVER_URL=mongodb://root:{mongodb_secret}@edu-db:27017/

KEYCLOAK_EDU_UI_SECRET={keycloak_eduui_secret}
KEYCLOAK_EDU_API_CLIENT_SECRET={keycloak_eduapi_secret}

LMN_API_BASE_URL=https://{data.DATA_LMN_EXTERNAL_DOMAIN}:8001/v1/

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

    if data.DATA_LE_USED:
        le_renew_script = f"""
#!/bin/bash

docker run --rm \
    --network edulution-ui_default \
    -v {EDULUTION_DIRECTORY}/data/certbot/etc:/etc/letsencrypt \
    -v {EDULUTION_DIRECTORY}/data/certbot/var:/var/lib/letsencrypt \
    certbot/certbot renew --quiet

cp {EDULUTION_DIRECTORY}/data/certbot/etc/live/{data.DATA_EDULUTION_EXTERNAL_DOMAIN}/fullchain.pem {EDULUTION_DIRECTORY}/data/traefik/ssl/cert.cert
cp {EDULUTION_DIRECTORY}/data/certbot/etc/live/{data.DATA_EDULUTION_EXTERNAL_DOMAIN}/privkey.pem {EDULUTION_DIRECTORY}/data/traefik/ssl/cert.key

docker kill -s HUP edulution-traefik
"""
        with open("/edulution-ui/renew_le_certificate.sh", "w") as f:
            f.write(le_renew_script)

    if os.path.exists("/edulution-ui/data/traefik/ssl/cert.cert") and os.path.exists("/edulution-ui/data/traefik/ssl/cert.key"):
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