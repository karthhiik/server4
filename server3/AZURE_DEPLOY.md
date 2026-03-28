# Azure Linux Web App Deployment (server3)

This service is prepared for Azure Web App for Containers on Linux.

## Runtime contract

- Container listens on `0.0.0.0:${PORT:-8000}`
- Health endpoint: `/healthz`
- Readiness endpoint: `/readyz`
- Diagnostics endpoint: `/diagnostics`

## Required Azure App Settings

Set at minimum:

- `WEBSITES_PORT=8000`
- `PORT=8000`
- All required application environment variables from `.env`

## Container image

Build context is repository root so shared package paths resolve:

```bash
docker build -f server3/Dockerfile -t <registry>/server3:latest .
```

## Azure checks

After deployment:

- `GET /healthz` should return `200`
- `GET /readyz` should return `200` when Mongo and Redis are reachable, otherwise `503`
- `GET /diagnostics` should return runtime diagnostics JSON

## Notes

- This image includes `server3/.env` for standalone container operation.
- For stronger security, prefer Azure App Settings / Key Vault in production and do not bake secrets into images.
