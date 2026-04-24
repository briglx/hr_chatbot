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
# 1. Check uv is installed
# -----------------------------------------------------------------------
if ! command -v uv &>/dev/null; then
  die "uv not found. Install it with:\n  curl -LsSf https://astral.sh/uv/install.sh | sh\n  or: brew install uv"
fi
ok "uv $(uv --version | cut -d' ' -f2) found"

# -----------------------------------------------------------------------
# 2. Check .env exists
# -----------------------------------------------------------------------
ENV_FILE="$ROOT_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  die ".env not found. Copy .env.example and fill in your values:\n  cp .env.example .env"
fi
log "Loading environment from $ENV_FILE"
set -a; source "$ENV_FILE"; set +a

# -----------------------------------------------------------------------
# 3. Check required env vars
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
# 4. Sync dependencies via uv
# -----------------------------------------------------------------------
log "Syncing dependencies ..."
cd "$ROOT_DIR"

if [[ -f "pyproject.toml" ]]; then
  # Preferred: uv manages the project with pyproject.toml + uv.lock
  uv sync --frozen
else
  # Fallback: legacy requirements.txt
  warn "No pyproject.toml found — falling back to requirements.txt"
  uv pip install --quiet -r requirements.txt
fi
ok "Dependencies up to date"

# -----------------------------------------------------------------------
# 5. Check Redis is reachable
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
# 6. Optional: remind about ngrok / Dev Tunnel
# -----------------------------------------------------------------------
warn "Teams requires a public HTTPS endpoint. If you haven't already:"
warn "  ngrok http 8000          (and update your Bot Framework messaging endpoint)"
warn "  devtunnel host -p 8000   (VS Code Dev Tunnels alternative)"
echo ""

# -----------------------------------------------------------------------
# 7. Start the app
# -----------------------------------------------------------------------
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
APP_ENV="${APP_ENV:-development}"
FRONTEND_DIR="${FRONTEND_DIR:-$ROOT_DIR/front_end}"

if [[ ! -d "$FRONTEND_DIR" ]]; then
  die "Frontend directory not found: $FRONTEND_DIR\nSet FRONTEND_DIR in .env if it's in a non-standard location."
fi

# Install frontend deps if node_modules is missing or package.json is newer
if [[ ! -d "$FRONTEND_DIR/node_modules" ]] || \
   [[ "$FRONTEND_DIR/package.json" -nt "$FRONTEND_DIR/node_modules" ]]; then
  log "Installing frontend dependencies ..."
  npm install --prefix "$FRONTEND_DIR" --silent
  ok "Frontend dependencies installed"
fi

# Trap Ctrl+C and kill both child processes cleanly
cleanup() {
  echo ""
  log "Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  ok "All processes stopped"
}
trap cleanup INT TERM

log "Starting backend on http://${HOST}:${PORT}  (env=${APP_ENV})"
log "Starting frontend in $FRONTEND_DIR"
echo ""

if [[ "$APP_ENV" == "development" ]]; then
  uv run uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --reload-dir app \
    --log-level info & 
  BACKEND_PID=$!
else
  # Staging / production: no --reload, multiple workers
  WORKERS="${WORKERS:-2}"
  uv run uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level info & 
  BACKEND_PID=$!
fi

npm run dev --prefix "$FRONTEND_DIR" &
FRONTEND_PID=$!

# Wait for either process to exit; if one dies, kill the other
wait -n "$BACKEND_PID" "$FRONTEND_PID"
EXIT_CODE=$?
cleanup
exit $EXIT_CODE