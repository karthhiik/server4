# Azure Env Sync for Production (Azure Portal GUI)

This repository now supports exporting app settings directly from each service `.env` file in a format that can be pasted into Azure Portal `Advanced edit`.

## What this solves

- No manual copy-paste of dozens of settings.
- One source of truth per service: `server2/.env`, `FASTAPI_COMMUNITY/.env`, `server3/.env`.
- Supports your current standalone container approach where each Docker image includes its own `.env`.

## Scripts added

- `scripts/export-azure-appsettings.ps1`
- `scripts/export-combined-env-manifest.ps1`
- `scripts/export-azure-portal-appsettings.ps1`

## 1) Export Azure Portal app settings JSON per service

From repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\export-azure-portal-appsettings.ps1 -Service server2
powershell -ExecutionPolicy Bypass -File .\scripts\export-azure-portal-appsettings.ps1 -Service fastapi_community
powershell -ExecutionPolicy Bypass -File .\scripts\export-azure-portal-appsettings.ps1 -Service server3
```

Generated files:

- `deploy/azure/server2.portal-appsettings.json`
- `deploy/azure/fastapi_community.portal-appsettings.json`
- `deploy/azure/server3.portal-appsettings.json`

## 2) Apply settings in Azure Portal (GUI only)

For each service Web App:

1. Open Azure Portal.
2. Go to your Web App.
3. Go to `Settings` -> `Environment variables`.
4. Select `App settings` tab.
5. Click `Advanced edit`.
6. Open the matching generated file from `deploy/azure/*.portal-appsettings.json`.
7. Paste full JSON array into `Advanced edit`.
8. Click `OK` then `Apply`.
9. Confirm restart when prompted.

## 3) Required Azure container port settings

Set these for each web app:

- `PORT=8000` for FASTAPI_COMMUNITY and server3
- `PORT=8080` for server2
- `WEBSITES_PORT` should match the same runtime port

In Portal, ensure these exist:

- server2: `PORT=8080`, `WEBSITES_PORT=8080`
- fastapi_community: `PORT=8000`, `WEBSITES_PORT=8000`
- server3: `PORT=8000`, `WEBSITES_PORT=8000`

## 4) Export one combined env manifest (all three services)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\export-combined-env-manifest.ps1
```

Generated file:

- `deploy/azure/combined-services.env.json`

This is useful for audits and release reviews across all services.

## 5) Runtime probe endpoints to validate after deploy

- server2: `/healthz`, `/readyz`, `/diagnostics`
- FASTAPI_COMMUNITY: `/healthz`, `/readyz`, `/diagnostics`
- server3: `/healthz`, `/readyz`, `/diagnostics`

## Note

These scripts export current `.env` values as-is (including secrets). Handle generated files securely and avoid sharing them in insecure channels.

## Optional CLI path

If needed later, CLI export is still available via `scripts/export-azure-appsettings.ps1`.
