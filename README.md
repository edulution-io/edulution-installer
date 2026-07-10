# EDULUTION Installer

## Quick Install

```bash
curl -fsSL https://get.edulution.io/installer | sudo bash
```

### Branch-Installation

```bash
curl -fsSL https://raw.githubusercontent.com/OWNER/REPOSITORY/BRANCH/apps/public-page/public/installer \
  | sudo bash -s -- --branch BRANCH \
      --image ghcr.io/OWNER/REPOSITORY \
      --source-repository OWNER/REPOSITORY
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
