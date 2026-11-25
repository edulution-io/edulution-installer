# EDULUTION Installer

## Quick Install

```bash
bash <(curl -s https://get.edulution.io/installer)
```

## Update an installation

Check whether an installation's `docker-compose.yml` and `edulution.env` match the release (read-only, the exit code tells the result). "Current" refers to these files: images are pulled only when an update is applied.

```bash
curl -fsSL https://get.edulution.io/update | sudo bash -s -- --check
```

Apply the update. The script shows what changes, asks for confirmation on the terminal, replaces `docker-compose.yml` with the release's template and then pulls the images and restarts the stack:

```bash
curl -fsSL https://get.edulution.io/update | sudo bash -s --
```

Declining changes nothing and exits with code 2. If pulling or restarting fails after the files were updated, running the script again finishes the restart. For unattended runs use `--yes`; `--compose-only` updates the files without pulling or restarting, and the next run without it restarts the stack:

```bash
curl -fsSL https://get.edulution.io/update | sudo bash -s -- --compose-only --yes
```

Other options: `--version X.Y.Z` (update to that release), `--check --json` (machine-readable report on stdout, the script's own messages go to stderr), `--discard-local-changes` (replace a locally modified `docker-compose.yml`) and `--migration ID` (run a major migration listed in the check output).

Tools that run the installer image directly instead of this script get the same exit codes, with two exceptions. The pending restart is tracked only by this script. For exit code 6, this script hands the container edu-api's environment as `docker compose config --format json` resolves it. A direct run reads `edulution.env` alone, unless `EDULUTION_UPDATE_RESOLVED_CONFIG` names such a file inside the container.

Keep local changes in `docker-compose.override.yml`, not in `docker-compose.yml`: the update replaces `docker-compose.yml` as a whole. Before every change the previous files are copied to `/srv/docker/edulution-ui/docker-compose-backups/` (readable by root only, as the copies of `edulution.env` hold its secrets). Old backups are not removed automatically; delete the ones you no longer need.

| Exit code | Meaning |
| --- | --- |
| 0 | Nothing to do (`--check`), or the update or migration succeeded |
| 10 | Update available, or a restart after the last update is still pending |
| 20 | `docker-compose.yml` has local modifications |
| 30 | Blocked by a major migration (`--migration ID`) |
| 1 | Error |
| 2 | Usage error, update declined, or confirmation missing (no terminal and no `--yes`) |
| 3 | Another update is running |
| 4 | Files changed since the check |
| 5 | Downgrade refused: the installation is newer than the target release (`--check` reports it before anything runs; pick the release with `--version`) |
| 6 | edu-api does not get both `MONGODB_USERNAME` and `MONGODB_PASSWORD` with a value (as `docker compose config` resolves them from `edulution.env` and `docker-compose.override.yml`), while the update or the restart would start the database with access control; create a database user and enter it first |

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

### Test on VMs

[`tools/vm-test`](tools/vm-test/README.md) sets up two throwaway KVM machines, an edulution server and a linuxmuster server. On them, a branch goes through the whole installation, including the linuxmuster setup, before it is released.

## Deployment

- **Public Page** — Automatically deployed to GitHub Pages via GitHub Actions on push to `main` or `dev`
- **Web Installer** — Docker image built via `docker-compose.yml` / `Dockerfile`

## Licence

Proprietary software of Digitale Schule Innovationsberatung GmbH (DSI), not open source. Anyone may run the installer, unmodified and free of charge, to install, configure and update edulution; copying, modifying and distributing it is not permitted, see [LICENSE](LICENSE). Netzint GmbH develops and operates it on DSI's behalf.

The build writes the licence and notice files of the packages in each frontend bundle to `third-party-licenses.txt` next to it. The container image carries `LICENSE` in `/app/`.

Manufacturer and licensor: Digitale Schule Innovationsberatung GmbH, Lammstr. 6, 77933 Lahr, Germany. Licensing enquiries: info@edulution.io. Report security vulnerabilities to security@edulution.io, as the [security policy](https://github.com/edulution-io/.github/blob/main/SECURITY.md) describes.
