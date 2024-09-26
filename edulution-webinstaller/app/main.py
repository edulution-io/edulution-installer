import base64
import json
import requests
import socket
import asyncio

from fastapi import FastAPI, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ldap3 import Server, Connection, ALL

class Token(BaseModel):
    token: str

class ExternalDomain(BaseModel):
    external_domain: str

class ExternalDomainWithLogin(BaseModel):
    external_domain: str
    binduser_dn: str
    binduser_pw: str

app = FastAPI()

app.mount("/css", StaticFiles(directory="css"), name="static")
app.mount("/img", StaticFiles(directory="img"), name="static")
app.mount("/js", StaticFiles(directory="js"), name="static")

with open("./html/site.html") as f:
    site = f.read()

@app.get("/")
def root():
    html_content = """
    <form method="POST" action="/install">
        <div class="form-group">
            <p>Füge hier deinen "Edulution-Setup-Token" ein:</p>
            <textarea class="form-control" rows="5" name="edulutionsetuptoken" id="edulutionsetuptoken" oninput="checkToken()" onfocus="checkToken()"></textarea>
        </div>
        <input type="submit" class="gradient-button" value="Installieren" id="btn_install" disabled></input>
    </form>
    <br>
    <hr>
    <br>
    <a href="#manual-install" data-bs-toggle="collapse" aria-expanded="false" aria-controls="manual-install">
    Manuelle Installation
    </a>
    <br>
    <form method="POST" action="/install" id="manual-install" class="collapse">
        <div class="form-group">
            <p>Externe-Server-Adresse</p>
            <div class="form-group">
                <input type="text" class="form-control" name="external_domain">
            </div>
        </div>
        <div class="form-group">
            <p>Bind-User-DN</p>
            <div class="form-group">
                <input type="text" class="form-control" name="binduser_dn">
            </div>
        </div>
        <div class="form-group">
            <p>Bind-User-Passwort</p>
            <div class="form-group">
                <input type="text" class="form-control" name="binduser_pw">
            </div>
        </div>
        <input type="submit" class="gradient-button" value="Installieren"></input>
    </form>
    """
    return HTMLResponse(content=site.replace("##CONTENT##", html_content), status_code=200)

@app.post("/install")
def install(edulutionsetuptoken: str = Form(None), external_domain: str = Form(None), binduser_dn: str = Form(None), binduser_pw: str = Form(None)):
    if edulutionsetuptoken is not None:
        data = base64.b64decode(edulutionsetuptoken.encode("utf-8"))
        data = json.loads(data.decode("utf-8"))
        external_domain = data["external_domain"]
        binduser_dn = data["binduser_dn"]
        binduser_pw = data["binduser_password"]

    if not external_domain or not binduser_dn or not binduser_pw:
        return RedirectResponse("/")

    html_content = f"""
    <h3>Überprüfung der Abhängigkeiten</h3>
    <br>
    <div class="card text-bg-dark">
        <div class="card-body">
            <div class="card-icon" id="api_status" edulution-external-domain="{external_domain}">
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
            <div class="card-icon" id="webdav_status" edulution-external-domain="{external_domain}">
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
            <div class="card-icon" id="ldap_status" edulution-external-domain="{external_domain}">
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
            <div class="card-icon" id="ldap-access_status" edulution-external-domain="{external_domain}" edulution-binduser-dn="{binduser_dn}" edulution-binduser-pw="{binduser_pw}">
                <i class="fa-solid fa-spinner fa-spin"></i>
            </div>
            <div class="card-text">Überprüfung der LDAP(s) Zugangsdaten</div>
            <div class="card-button">
                <button type="button" class="btn btn-secondary" onclick="checkLDAPAccessStatus()" id="ldap-access_status_retry">Erneut prüfen</button>
            </div>
        </div>
    </div>
    <form method="POST" action="/finish" id="finish_button" class="collapse">
        <input type="hidden" name="external_domain" value="{external_domain}">
        <input type="hidden" name="binduser_dn" value="{binduser_dn}">
        <input type="hidden" name="binduser_pw" value="{binduser_pw}">
        <input type="submit" class="gradient-button" value="Abschließen"></input>
    </form>
    <script type="text/javascript">
        checkAll();
    </script>
    """
    return HTMLResponse(content=site.replace("##CONTENT##", html_content), status_code=200)

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
    
@app.post("/check-api-status")
def checkAPIStatus(data: ExternalDomain):
    try:
        result = requests.get("https://" + data.external_domain + ":8001", verify=False, timeout=3)
        if result.status_code == 200:
            return True
        return False
    except:
        return False
    
@app.post("/check-webdav-status")
def checkWebDAV(data: ExternalDomain):
    try:
        result = requests.get("https://" + data.external_domain + ":443", verify=False, timeout=3)
        if result.status_code == 200:
            return True
        return False
    except:
        return False
    
@app.post("/check-ldap-status")
def checkLDAP(data: ExternalDomain):
    try:
        server = Server(data.external_domain, port=636, get_info=ALL, connect_timeout=3, use_ssl=True)
        conn = Connection(server, auto_bind=True)
        if conn.bind():
            return True
        return False
    except Exception as e:
        print(e)
        return False
    
@app.post("/check-ldap-access-status")
def checkLDAP(data: ExternalDomainWithLogin):
    try:
        server = Server(data.external_domain, port=636, get_info=ALL, connect_timeout=3, use_ssl=True)
        conn = Connection(server, user= data.binduser_dn, password=data.binduser_pw, auto_bind=True)
        if conn.bind():
            return True
        return False
    except Exception as e:
        return False
    
@app.post("/finish")
def finish(background_tasks: BackgroundTasks, edulutionsetuptoken: str = Form(None), external_domain: str = Form(None), binduser_dn: str = Form(None), binduser_pw: str = Form(None)):
    if edulutionsetuptoken is not None:
        data = base64.b64decode(edulutionsetuptoken.encode("utf-8"))
        data = json.loads(data.decode("utf-8"))
        external_domain = data["external_domain"]
        binduser_dn = data["binduser_dn"]
        binduser_pw = data["binduser_password"]

    if not external_domain or not binduser_dn or not binduser_pw:
        return RedirectResponse("/")
    
    background_tasks.add_task(createEdulutionEnvFile, external_domain, binduser_dn, binduser_pw)

    html_content = f"""
        <h3>Konfiguration abgeschlossen</h3>
        <h2><i class="fa-solid fa-spinner fa-spin"></i></h2>
        <p>Die edulutionUI wird nun installiert...</p>
        <p>vSie werden automatisch weitergeleitet, wenn die Installation abgeschlossen ist.</p>
        <script type="text/javascript">
            waitforUI();
        </script>
    """
    return HTMLResponse(content=site.replace("##CONTENT##", html_content), status_code=200)

@app.api_route("/{path_name:path}")
def catch_all():
    return RedirectResponse("/")

def createEdulutionEnvFile(external_domain: str, binduser_dn: str, binduser_pw: str):
    with open("/edulution-ui/edulution.env", "w") as f:
        f.write(external_domain)
    
    loop = asyncio.get_event_loop()
    loop.stop()