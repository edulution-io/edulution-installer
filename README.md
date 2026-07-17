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

### Docker

```bash
npm run build:webinstaller    # Build frontend first
docker compose up --build     # Build & run container
```

The web installer runs on `https://localhost:443`.

## Deployment

- **Public Page** — Automatically deployed to GitHub Pages via GitHub Actions on push to `main` or `dev`
- **Web Installer** — Docker image built via `docker-compose.yml` / `Dockerfile`

### `get` image (self-hosted download page)

For running `get.edulution.io` without GitHub Pages (e.g. when the repository is
private), the `get` image serves the download page together with the `installer`
bootstrap script and the config templates. It is built by
`.github/workflows/build-get-docker.yml` (from `Dockerfile.get` + the built
`public-page` bundle) and published as `ghcr.io/edulution-io/edulution-installer-get`.

Run it behind your reverse proxy for `get.edulution.io`:

```bash
docker run -d --name edulution-get -p 80:80 \
  ghcr.io/edulution-io/edulution-installer-get:main
```

Because the `installer` keeps downloading templates from `get.edulution.io/download/*`,
the install flow is unchanged.
