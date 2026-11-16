# EDULUTION Installer

## Quick Install

```bash
bash <(curl -s https://get.edulution.io/installer)
```

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

## Licence

Proprietary software of Digitale Schule Innovationsberatung GmbH (DSI), not open source. Anyone may run the installer, unmodified and free of charge, to install, configure and update edulution; copying, modifying and distributing it is not permitted, see [LICENSE](LICENSE). Netzint GmbH develops and operates it on DSI's behalf.

The build writes the licence and notice files of the packages in each frontend bundle to `third-party-licenses.txt` next to it. The container image carries `LICENSE` in `/app/`.

Manufacturer and licensor: Digitale Schule Innovationsberatung GmbH, Lammstr. 6, 77933 Lahr, Germany. Licensing enquiries: info@edulution.io. Report security vulnerabilities to security@edulution.io, as the [security policy](https://github.com/edulution-io/.github/blob/main/SECURITY.md) describes.
