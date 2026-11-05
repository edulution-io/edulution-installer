# EDULUTION Installer

## Quick Install

```bash
bash <(curl -s https://get.edulution.io/installer)
```

## Update an installation

Check whether an installation is current (read-only, the exit code tells the result):

```bash
curl -fsSL https://get.edulution.io/update | sudo bash -s -- --check
```

Apply the update. The script shows what changes, asks for confirmation on the terminal, replaces `docker-compose.yml` with the release's template and then pulls the images and restarts the stack:

```bash
curl -fsSL https://get.edulution.io/update | sudo bash -s --
```

Declining changes nothing and exits with code 2. For unattended runs use `--yes`; `--compose-only` updates the files without pulling or restarting:

```bash
curl -fsSL https://get.edulution.io/update | sudo bash -s -- --compose-only --yes
```

Other options: `--version X.Y.Z` (update to that release), `--check --json` (machine-readable report on stdout, the script's own messages go to stderr), `--discard-local-changes` (replace a locally modified `docker-compose.yml`) and `--migration ID` (run a major migration listed in the check output).

Tools that run the installer image directly instead of this script get the same exit codes.

Keep local changes in `docker-compose.override.yml`, not in `docker-compose.yml`: the update replaces `docker-compose.yml` as a whole. Before every change the previous files are copied to `/srv/docker/edulution-ui/docker-compose-backups/`.

| Exit code | Meaning |
| --- | --- |
| 0 | Nothing to do (`--check`), or the update or migration succeeded |
| 10 | Update available |
| 20 | `docker-compose.yml` has local modifications |
| 30 | Blocked by a major migration (`--migration ID`) |
| 1 | Error |
| 2 | Usage error or confirmation missing (no terminal and no `--yes`) |
| 3 | Another update is running |
| 4 | Files changed since the check |
| 5 | Downgrade refused: the installation is newer than the target release (`--check` reports it before anything runs; pick the release with `--version`) |

Any other non-zero code (for example Docker's 125 to 127) means the update container could not be started.

## Project Structure

This is an Nx monorepo containing:

- **apps/public-page/** — React (Vite) download page deployed to GitHub Pages (`get.edulution.io`)
- **apps/webinstaller/** — React (Vite) installer UI
- **apps/webinstaller-api/** — Python (FastAPI) backend for the installer
- **libs/shared-ui/** — Shared UI component library

## Development

### Public Page

```bash
npm install
npm run dev:public     # Dev server on http://localhost:4200
npm run build:public   # Build to dist/apps/public-page/
npm run lint           # Lint all projects
```

### Web Installer

```bash
npm run dev:webinstaller      # Frontend dev server on http://localhost:4201
npm run dev:webinstaller-api  # Backend dev server on http://localhost:8000
npm run build:webinstaller    # Build frontend to dist/apps/webinstaller/
```

The backend requires a session. Export `INSTALLER_TOKEN` before `npm run dev:webinstaller-api` so the token survives reloads, and open `http://localhost:8000/?token=<token>` once to get the session cookie.

### Docker

```bash
npm run build:webinstaller    # Build frontend first
docker compose up --build     # Build & run container
```

The web installer runs on `https://localhost:443/?token=<token>`. The token is taken from `INSTALLER_TOKEN`; without it, the API generates one and prints it at startup (`docker compose logs`).

## Deployment

- **Public Page** — Automatically deployed to GitHub Pages via GitHub Actions on push to `main` or `dev`
- **Web Installer** — Docker image built via `docker-compose.yml` / `Dockerfile`
