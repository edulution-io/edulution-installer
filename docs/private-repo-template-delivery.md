# Plan: Template-/Installer-Auslieferung bei privatem Repository

## Ausgangslage (aktuell, public Repo)

- **`get.edulution.io`** ist die GitHub-Pages-Seite des `public-page`-Apps. Sie
  liefert das Bootstrap-Script **`installer`** und die Vorlagen
  **`download/*.template`** (`docker-compose.yml`, `realm-edulution.json`,
  `traefik.yml`, `edulution-default.yml`, `edulution-default-le.yml`).
- Das `installer`-Script lädt die Vorlagen zur Laufzeit von
  `https://get.edulution.io/download/*.template`.
- Der `--branch`-Testmodus lädt Script/Vorlagen von
  `raw.githubusercontent.com/<repo>/<branch>/apps/public-page/public/...`.
- Die Installer-/edulution-Images liegen auf **ghcr.io**.

## Was beim Umstellen auf privat wegfällt

- **GitHub Pages (öffentlich)** und **`raw.githubusercontent.com` ohne Token**
  funktionieren für private Repos nicht mehr. Damit brechen sowohl
  `get.edulution.io/download/*` als auch der `--branch`-Testpfad.

## Was NICHT betroffen ist

- **ghcr-Images:** Die Sichtbarkeit eines ghcr-Packages ist **unabhängig** von
  der Repo-Sichtbarkeit. Die Images können öffentlich bleiben → `docker pull`
  funktioniert weiter. (Einmalig die Package-Visibility der relevanten Images
  auf *public* setzen.) Die Vorlagen sind ohnehin keine Geheimnisse, aber der
  Quellcode bleibt privat.

## Optionen

### Option A (empfohlen): Vorlagen ins Installer-Image + winziges öffentliches Bootstrap

- Die `download/*.template` werden ins Installer-Image kopiert (Dockerfile
  `COPY`). Beim Container-Start (oder per `docker cp` aus dem Script) werden sie
  in das gemountete `/edulution-ui` materialisiert.
- Damit braucht **nur noch das kleine `installer`-Bootstrap-Script** eine
  öffentliche URL — keine öffentliche Vorlagen-Fläche mehr.
- Öffentliches Hosting des Bootstrap-Scripts: kleines **Public-Repo
  `edulution-io/get`** (nur Script + Pages → `get.edulution.io`) oder ein
  netzint-Webserver. Beides nicht geheim.
- **Pro:** keine Template-Drift (Vorlagen = Image-Version), minimale öffentliche
  Angriffsfläche, `--branch`-Test braucht nur noch den (public) Image-Tag.
- **Con:** Install-Flow leicht umbauen (Vorlagen aus Image statt `curl`).

### Option B: Separates Public-Assets-Repo

- `installer` + `download/*` in ein kleines Public-Repo auslagern, dessen Pages
  `get.edulution.io` bedient. Haupt-Repo privat.
- CI im privaten Repo spiegelt die Vorlagen bei jedem Release ins Public-Repo.
- **Pro:** Install-UX unverändert (`get.edulution.io/download` bleibt).
- **Con:** zwei Repos + Sync-Mechanismus, Template-Drift bleibt möglich.

### Option C: Eigene Infra (netzint)

- Static-Hosting auf netzint (Server/S3/CDN), CI lädt bei Release hoch;
  `get.edulution.io` zeigt dorthin.
- **Pro:** volle Kontrolle, unabhängig von GitHub. **Con:** Infra + CI-Deploy.

### Verworfen

- **Private Pages (Access-Control):** verlangt Login der Besucher → für ein
  öffentliches Install-Endpoint ungeeignet.
- **Release-Assets eines privaten Repos:** Download braucht Auth-Token.

## Branch-Testing (`--branch`) bei privatem Repo

- `raw.githubusercontent.com` bricht. Mit **Option A** ist das gelöst: der
  Branch-Test braucht nur den öffentlichen Image-Tag
  (`ghcr.io/edulution-io/edulution-installer:<branch>`), die Vorlagen kommen aus
  dem Image. Das Bootstrap-Script holt man aus dem Public-`get`-Repo oder einem
  lokalen Checkout.
- Ohne Option A müsste der Tester ein PAT hinterlegen (`curl -H "Authorization:
  token ..."` bzw. `gh api`).

## Empfehlung

**Option A** (Vorlagen ins Image) + ghcr-Packages öffentlich + kleines
Public-`get`-Repo fürs Bootstrap-Script. Das löst Privatsetzung, Template-Drift
und Branch-Testing in einem Schritt.

## Umsetzungsschritte (separater PR/Branch)

1. `Dockerfile`: `download/*.template` ins Image kopieren (z. B. nach
   `/app/templates`).
2. Container-Start (`startup.sh`) oder `installer`: Vorlagen nach
   `/edulution-ui` materialisieren; die `get.edulution.io/download`-Downloads im
   `installer` entfernen.
3. ghcr-Packages der Installer-/edulution-Images auf *public* setzen.
4. Public-Repo `edulution-io/get` mit dem Bootstrap-`installer` + Pages →
   `get.edulution.io`.
5. CI: Bootstrap-Script bei Release ins `get`-Repo spiegeln.
6. `installer --branch`: nur noch Image-Tag nutzen (kein `raw`-Zugriff mehr).

## Zusammenhang mit den LE-Grundproblem-Fixes (dieser Branch)

Die auf `feat/le-hardening` behobenen Punkte sind unabhängig von der
Auslieferung und gelten weiter:

- `EDULUTION_DIRECTORY` ist ein **fester Container-Pfad** (`/edulution-ui`) statt
  einer Env, die auf den Host-Pfad zeigte — das war die Ursache dafür, dass die
  Let's-Encrypt-Konfig ins Leere geschrieben wurde.
- `acme.json`/`acmedns.json` werden **nur angelegt, wenn nicht vorhanden** und
  auf `0600` gesetzt (keine Zerstörung bestehender Zertifikate/Registrierungen,
  keine world-readable Credentials).

## Weitere LE-Reworks (Vorschlag, noch offen)

- **Traefik-Configs als Daten statt f-String:** `dict` + `yaml.safe_dump()` statt
  handgezählter Einrückung; Wildcard wird damit ein Datenfeld statt Regex.
- **Ein einziges LE-Template** (Resolver am EntryPoint) statt der Doppelpflege
  `edulution-default.yml` ↔ `edulution-default-le.yml`.
- **CNAME-Preflight:** `_acme-challenge.<domain>` vor dem Durchlauf wirklich
  auflösen und gegen `<subdomain>.acme-dns.netzint.de` prüfen.
- **Zertifikatsstatus live** im Finish-Screen (acme.json / Traefik-Log pollen).
- **LE-Staging (`caServer`)** als Trockenlauf gegen Rate-Limits.
