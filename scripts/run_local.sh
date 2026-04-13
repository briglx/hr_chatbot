#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------
# run_local.sh — start the HR AI chatbot for local development
# -----------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# -----------------------------------------------------------------------
# Colours
# -----------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # no colour

log()  { echo -e "${CYAN}[hr-bot]${NC} $*"; }
ok()   { echo -e "${GREEN}[hr-bot]${NC} $*"; }
warn() { echo -e "${YELLOW}[hr-bot]${NC} $*"; }
die()  { echo -e "${RED}[hr-bot] ERROR:${NC} $*" >&2; exit 1; }

# -----------------------------------------------------------------------
# 1. Check .env exists
# -----------------------------------------------------------------------
ENV_FILE="$ROOT_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  die ".env not found. Copy .env.example and fill in your values:\n  cp .env.example .env"
fi
log "Loading environment from $ENV_FILE"
set -a; source "$ENV_FILE"; set +a

# -----------------------------------------------------------------------
# 2. Check required env vars
# -----------------------------------------------------------------------
REQUIRED_VARS=(
  AZURE_OPENAI_ENDPOINT
  AZURE_OPENAI_API_KEY
  REDIS_URL
)

missing=()
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    missing+=("$var")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  die "Missing required environment variables:\n  ${missing[*]}\nCheck your .env file."
fi
ok "Environment variables OK"

# -----------------------------------------------------------------------
# 3. Check Python virtual environment
# -----------------------------------------------------------------------
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  if [[ -d "$ROOT_DIR/.venv" ]]; then
    log "Activating .venv"
    source "$ROOT_DIR/.venv/bin/activate"
  else
    warn "No virtual environment found. Creating .venv ..."
    python3 -m venv "$ROOT_DIR/.venv"
    source "$ROOT_DIR/.venv/bin/activate"
    pip install --quiet --upgrade pip
    pip install --quiet -r "$ROOT_DIR/requirements.txt"
    ok "Dependencies installed"
  fi
fi

# -----------------------------------------------------------------------
# 4. Check Redis is reachable
# -----------------------------------------------------------------------
log "Checking Redis connection ..."
REDIS_HOST=$(echo "${REDIS_URL}" | sed -E 's|redis://([^:/]+).*|\1|')
REDIS_PORT=$(echo "${REDIS_URL}" | sed -E 's|redis://[^:]+:([0-9]+).*|\1|')
REDIS_PORT="${REDIS_PORT:-6379}"

if ! command -v redis-cli &>/dev/null; then
  warn "redis-cli not found — skipping Redis connectivity check"
elif ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &>/dev/null; then
  warn "Redis not reachable at ${REDIS_HOST}:${REDIS_PORT}."
  warn "Start it with:  docker run -d -p 6379:6379 redis:7-alpine"
  read -rp "Continue anyway? [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]] || exit 1
else
  ok "Redis reachable at ${REDIS_HOST}:${REDIS_PORT}"
fi

# -----------------------------------------------------------------------
# 5. Optional: remind about ngrok / Dev Tunnel
# -----------------------------------------------------------------------
warn "Teams requires a public HTTPS endpoint. If you haven't already:"
warn "  ngrok http 8000          (and update your Bot Framework messaging endpoint)"
warn "  devtunnel host -p 8000   (VS Code Dev Tunnels alternative)"
echo ""

# -----------------------------------------------------------------------
# 6. Start the app
# -----------------------------------------------------------------------
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
APP_ENV="${APP_ENV:-development}"

log "Starting uvicorn on http://${HOST}:${PORT}  (env=${APP_ENV})"
echo ""

cd "$ROOT_DIR"

if [[ "$APP_ENV" == "development" ]]; then
  exec uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --reload-dir app \
    --log-level info
else
  # Staging / production: no --reload, multiple workers
  WORKERS="${WORKERS:-2}"
  exec uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level info
fi
