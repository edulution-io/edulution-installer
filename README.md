# EDULUTION Installer

## Quick Install

```bash
bash <(curl -s https://get.edulution.io/installer)
```

## Project Structure

This is an Nx monorepo containing:

- **apps/public-page/** — React (Vite) download page deployed to GitHub Pages (`get.edulution.io`)
- **libs/shared-ui/** — Shared UI component library
- **edulution-webinstaller/** — Python (FastAPI) web installer served via Docker

## Development

### Public Page

```bash
npm install
npm run dev:public     # Dev server on http://localhost:4200
npm run build:public   # Build to dist/apps/public-page/
npm run lint           # Lint all projects
```

### Web Installer (Docker)

```bash
docker compose up --build
```

The web installer runs on `https://localhost:443`.

## Deployment

- **Public Page** — Automatically deployed to GitHub Pages via GitHub Actions on push to `main` or `dev`
- **Web Installer** — Docker image built via `docker-compose.yml` / `Dockerfile`
