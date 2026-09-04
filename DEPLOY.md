# Deployment

Requires Docker Engine 20.10+ with the Compose plugin. Ports 8123 (web) and
27017 (MongoDB) must be free. Nothing else is installed on the host.

## 1. Configure

```bash
cp .env.template .env
```

Edit `.env`:

| Variable | Required | Description |
|---|---|---|
| `MONGO_INITDB_ROOT_USERNAME` | yes | MongoDB user, created on first boot only. |
| `MONGO_INITDB_ROOT_PASSWORD` | yes | Its password. Set before the first start. |
| `MONGO_DB` | yes | Database name. Must stay `mapa-ciencia-db` to match the dump. |
| `MONGO_HOST` | yes | `mongo` (the compose service). Only change if running the API outside Docker. |
| `MONGO_PORT` | yes | `27017`. Used for both the host mapping and the internal connection. |
| `API_PORT` | yes | Port inside the container. Keep `8000`; the host port is set in `docker-compose.yml`. |
| `BASIC_AUTH_USERNAME` | yes | Web UI login user. |
| `BASIC_AUTH_PASSWORD` | yes | Web UI login password. |
| `JWT_SECRET` | yes | Session signing key. Generate with `openssl rand -hex 32`. |
| `GEMINI_API_KEY` | no | Generating new summaries/embeddings via Gemini. |
| `OLLAMA_HOST` / `OLLAMA_API_KEY` | no | Same, via a self-hosted Ollama server. |
| `LOCAL_EMBEDDING_HOST` | no | Local embedding service, if one is running. |
| `INTERNAL_SWAGGER_KEY` | no | Internal-only endpoints in `/docs`. |
| `DEFAULT_*` | yes | Tags/models the UI reads by default. Leave as shipped — they match the dump. |

The app will not start if any required value is empty. Optional keys can be left
blank: all data in the dump is pre-computed, so browsing, search and the graph
work without them. To add one later, edit `.env` and
`docker compose restart backend`.

## 2. Build and start

```bash
docker compose up -d --build
```

First build takes a few minutes. Compose waits for MongoDB to be healthy before
starting the API. Check with `docker compose ps` — both services `Up`.

## 3. Restore the database

Once, after the first start. Set `DUMP` to your dump file:

```bash
DUMP=backup_db_3_09_26.gz          # the .gz you were given
source .env

docker compose cp "$DUMP" mongo:/tmp/dump.gz
docker compose exec mongo mongorestore \
  -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase admin \
  --gzip --archive=/tmp/dump.gz
```

The dump carries its own database name and indexes. Add `--drop` when restoring
over an existing database.

## 4. Verify

```bash
docker compose exec mongo mongosh -u "$MONGO_INITDB_ROOT_USERNAME" \
  -p "$MONGO_INITDB_ROOT_PASSWORD" --quiet \
  --eval 'db.getSiblingDB("mapa-ciencia-db").Researcher.countDocuments({})'
```

Open `http://<host>:8123` and log in with `BASIC_AUTH_USERNAME` /
`BASIC_AUTH_PASSWORD`. API docs at `/docs`.

## Common commands

```bash
docker compose logs -f backend    # logs
docker compose restart backend    # apply an .env change
docker compose down               # stop, data preserved
docker compose down -v            # stop and delete the database
```

Back up the database:

```bash
source .env
docker compose exec mongo mongodump \
  -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase admin \
  --db mapa-ciencia-db --gzip --archive=/tmp/dump.gz
docker compose cp mongo:/tmp/dump.gz ./backup-$(date +%F).gz
```
