# hr_chatbot/auth.py

import time
import requests
import structlog
from app.config.settings import get_settings, AppEnv

logger = structlog.get_logger(__name__)

_token_cache: dict = {"access_token": None, "expires_at": 0}

s = get_settings()

# ------------------------------------------------------------------
# PRODUCTION: Client Credentials against YOUR Auth0 API
# ------------------------------------------------------------------
def _get_token_client_credentials() -> str:
    """
    Uses hr_chatbot's own client_id/secret to get a token scoped
    to your Kong gateway API (not the Auth0 Management API).
    """
    domain = s.auth0_domain          # e.g. mycompany.us.auth0.com
    client_id = s.auth0_client_id    # hr_chatbot Application → Client ID
    client_secret = s.auth0_client_secret
    audience = s.auth0_audience      # https://api.mycompany.com  ← your API identifier

    resp = requests.post(
        f"https://{domain}/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": audience,                 # MUST be your API, not auth0.com/api/v2
            "scope": "openai:invoke",             # custom scope you created on your API
        },
        headers={"Content-Type": "application/json"},
        timeout=10,
    )

    if resp.status_code == 401:
        raise RuntimeError(
            "Auth0 rejected client credentials. Check that:\n"
            "  1. AUTH0_AUDIENCE matches your API identifier exactly\n"
            "  2. hr_chatbot app is authorized against that API (not Management API)\n"
            "  3. The openai:invoke scope is granted to the app"
        )

    resp.raise_for_status()
    return resp.json()["access_token"]


# ------------------------------------------------------------------
# LOCAL DEV: auth0 CLI token
#
# One-time setup:
#   brew install auth0
#   auth0 login
#   export AUTH0_DEV_TOKEN=$(auth0 test token \
#       --client-id $AUTH0_CLIENT_ID \
#       --audience $AUTH0_AUDIENCE \
#       --scopes "openai:invoke")
#
# Or add to .envrc / direnv so it auto-refreshes.
# ------------------------------------------------------------------
def _get_dev_token_from_env() -> str:
    token = s.auth0_dev_token
    if not token:
        raise EnvironmentError(
            "\nAUTH0_DEV_TOKEN is not set.\n"
            "Run the following to get a local dev token:\n\n"
            "  auth0 login\n"
            "  export AUTH0_DEV_TOKEN=$(auth0 test token \\\n"
            "      --client-id $AUTH0_CLIENT_ID \\\n"
            "      --audience $AUTH0_AUDIENCE \\\n"
            "      --scopes 'openai:invoke')\n"
        )
    return token


# ------------------------------------------------------------------
# Validate the token looks sane before using it
# Catches common mistakes like accidentally using a Management API token
# ------------------------------------------------------------------
def _validate_token_audience(token: str) -> None:
    """
    JWT payload is base64-encoded — decode it without verifying
    the signature just to check we have the right audience.
    Signature verification is Kong's job.
    """
    import base64
    import json

    try:
        payload_b64 = token.split(".")[1]
        # Pad base64 if needed
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))

        audience = payload.get("aud", "")
        expected = s.auth0_audience

        # aud can be a string or a list
        aud_list = [audience] if isinstance(audience, str) else audience

    

        if not any(expected in a for a in aud_list):
            raise ValueError(
                f"Token audience {aud_list} does not match AUTH0_AUDIENCE={expected}.\n"
                "You may have accidentally fetched a Management API token.\n"
                "Re-run: auth0 test token --audience $AUTH0_AUDIENCE"
            )
        
        return payload
    
    except (IndexError, KeyError):
        pass  # Malformed token — let Kong reject it with a clear 401


# ------------------------------------------------------------------
# Unified token getter with in-memory cache
# ------------------------------------------------------------------
def get_access_token(app_env=None, force_refresh=False) -> str:
    print("HELLO")
    logger.debug("fetching_access_token")
    
    now = time.time()
    if not force_refresh and _token_cache["access_token"] and now < _token_cache["expires_at"] - 30:
        logger.debug("using_cached_access_token", expires_in=int(_token_cache["expires_at"] - now))
        return _token_cache["access_token"]

   
    if app_env is None:
        app_env = s.app_env

    if app_env == AppEnv.DEVELOPMENT:
        logger.debug("fetching_dev_token_from_env")
        access_token = _get_dev_token_from_env()
    else:
        logger.debug("fetching_token_client_credentials")
        access_token = _get_token_client_credentials()

    logger.debug("validating_token_audience")
    payload = _validate_token_audience(access_token)

    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = now + 3600
    return (payload, access_token)
