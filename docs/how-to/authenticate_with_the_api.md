# Authenticate with the API

The open_datEAUbase API uses bearer tokens. Most endpoints require authentication; only health checks and login/signup are public.

This guide shows how to obtain a token and use it in API requests.

## Get a token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_user", "password": "your_password"}'
```

The response contains an `access_token`:

```json
{"access_token": "eyJ...", "token_type": "bearer"}
```

## Use the token

Include the token in the `Authorization` header for all protected requests:

```bash
curl http://localhost:8000/api/v1/campaigns \
  -H "Authorization: Bearer eyJ..."
```

## Service tokens for machine clients

For the importer or other unattended scripts, set `API_SERVICE_TOKEN` in the API environment and send it as a bearer token. This is useful for CI pipelines or data-ingestion containers.

## See also

- [API Reference](../reference/api/index.md) — interactive endpoint reference.
- [Ingest Sensor CSV](ingest_sensor_csv.md) — authenticated example.
