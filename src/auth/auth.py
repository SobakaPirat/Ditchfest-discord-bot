import base64
import json
import logging
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth

from src.utils.config import get_env_key, set_env_key

logger = logging.getLogger(__name__)

ubi_url = "https://public-ubiservices.ubi.com/v3/profiles/sessions"
ubi_appid = "86263886-327a-4328-ac69-527f0d20a237"
nadeo_url = "https://prod.trackmania.core.nadeo.online/v2/authentication/token/basic"
nadeo_refresh_url = (
    "https://prod.trackmania.core.nadeo.online/v2/authentication/token/refresh"
)
oauth_url = "https://api.trackmania.com/api/access_token"


# Authenticates with Ubisoft and stores Nadeo access token,
#   and Nadeo liveservices token, in .env
def authenticate() -> None:
    user_agent = get_env_key("USER_AGENT")
    login = get_env_key("UBI_LOGIN")
    password = get_env_key("UBI_PASSWORD")
    client_id = get_env_key("CLIENT_ID")
    client_secret = get_env_key("CLIENT_SECRET")

    ubi_auth = HTTPBasicAuth(login, password)

    # Get nadeo access token
    nadeo_headers = {
        "Content-Type": "application/json",
        "User-Agent": user_agent,
    }

    # audience NadeoServices is used by default, so no need to specify audience in request body
    nadeo_res = requests.post(nadeo_url, headers=nadeo_headers, auth=ubi_auth)
    nadeo_res = nadeo_res.json()
    if nadeo_res.get("message"):
        logger.error("Invalid credentials!")
    access_token = nadeo_res["accessToken"]
    refresh_token = nadeo_res["refreshToken"]
    set_env_key("NADEO_ACCESS_TOKEN", str(access_token))
    set_env_key("NADEO_REFRESH_TOKEN", str(refresh_token))

    # Another nadeo request with "NadeoLiveServices" audience
    nadeo_body = {"audience": "NadeoLiveServices"}
    nadeo_res = requests.post(
        nadeo_url, headers=nadeo_headers, json=nadeo_body, auth=ubi_auth
    )
    nadeo_res = nadeo_res.json()

    access_token = nadeo_res["accessToken"]
    refresh_token = nadeo_res["refreshToken"]
    set_env_key("NADEO_LIVESERVICES_ACCESS_TOKEN", str(access_token))
    set_env_key("NADEO_LIVESERVICES_REFRESH_TOKEN", str(refresh_token))

    oauth_headers = {"content-type": "application/x-www-form-urlencoded"}
    oauth_body = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}"
    oauth_res = requests.post(oauth_url, headers=oauth_headers, data=oauth_body)
    oauth_res = oauth_res.json()
    oauth_token = oauth_res["access_token"]
    current_time = int(datetime.now().timestamp())
    oauth_expiration = current_time + oauth_res["expires_in"]
    set_env_key("OAUTH_TOKEN", str(oauth_token))
    set_env_key("OAUTH_EXPIRATION", str(oauth_expiration))


# Updates the nadeo access token in .env
def refresh_access_token() -> None:
    refresh_token = get_env_key("NADEO_REFRESH_TOKEN")
    user_agent = get_env_key("USER_AGENT")

    nadeo_headers = {
        "Content-Type": "application/json",
        "Authorization": "nadeo_v1 t=" + refresh_token,
        "User-Agent": user_agent,
    }
    # audience NadeoServices is used by default, so no need to specify audience in request body

    nadeo_res = requests.post(nadeo_refresh_url, headers=nadeo_headers)
    nadeo_res = nadeo_res.json()

    access_token = nadeo_res["accessToken"]
    refresh_token = nadeo_res["refreshToken"]
    set_env_key("NADEO_ACCESS_TOKEN", str(access_token))
    set_env_key("NADEO_REFRESH_TOKEN", str(refresh_token))


def refresh_live_access_token() -> None:
    refresh_token = get_env_key("NADEO_LIVESERVICES_REFRESH_TOKEN")
    user_agent = get_env_key("USER_AGENT")

    # LiveServices
    nadeo_headers = {
        "Content-Type": "application/json",
        "Authorization": "nadeo_v1 t=" + refresh_token,
        "User-Agent": user_agent,
    }

    nadeo_res = requests.post(nadeo_refresh_url, headers=nadeo_headers)
    nadeo_res = nadeo_res.json()

    try:
        access_token = nadeo_res["accessToken"]
        refresh_token = nadeo_res["refreshToken"]
        set_env_key("NADEO_LIVESERVICES_ACCESS_TOKEN", str(access_token))
        set_env_key("NADEO_LIVESERVICES_REFRESH_TOKEN", str(refresh_token))

    except KeyError as e:
        logger.info(f"Refresh live services token: {e}")


def refresh_oauth_token() -> None:
    client_id = get_env_key("CLIENT_ID")
    client_secret = get_env_key("CLIENT_SECRET")

    oauth_headers = {"content-type": "application/x-www-form-urlencoded"}
    oauth_body = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}"

    try:
        oauth_res = requests.post(oauth_url, headers=oauth_headers, data=oauth_body)
        oauth_res = oauth_res.json()
        oauth_token = oauth_res["access_token"]
        oauth_expires = oauth_res["expires_in"]
        set_env_key("OAUTH_TOKEN", str(oauth_token))
        set_env_key("OAUTH_EXPIRES", str(oauth_expires))
    except KeyError as e:
        logger.info(f"Refresh oauth token: {e}")


# Decodes the stored nadeo access token,
#   and refreshes it if needed.
def check_token_refresh() -> None:
    # Normal token
    token = get_env_key("NADEO_ACCESS_TOKEN")

    # Make sure token is not empty
    if token == "":
        authenticate()
        logger.info("check_token_refresh: Authenticated")
        return

    (expiration, refresh_possible_after) = decode_access_token(token)

    current_time = int(datetime.now().timestamp())
    if current_time > expiration:
        # Authentication required
        authenticate()
        logger.info("check_token_refresh: Authenticated")
        return

    elif current_time > refresh_possible_after:
        # Just refresh the token
        refresh_access_token()
        logger.info("check_token_refresh: Token refreshed")
    else:
        pass
        # logger.info("check_token_refresh: No token refresh needed")

    # live
    token = get_env_key("NADEO_LIVESERVICES_ACCESS_TOKEN")

    # Make sure token is not empty
    if token == "":
        authenticate()
        logger.info("check_token_refresh: Authenticated")
        return

    (expiration, refresh_possible_after) = decode_access_token(token)

    current_time = int(datetime.now().timestamp())
    if current_time > expiration:
        # Authentication required
        authenticate()
        logger.info("check_token_refresh: Authenticated")
    elif current_time > refresh_possible_after:
        # Just refresh the token
        refresh_live_access_token()
        logger.info("check_token_refresh: LIVE token refreshed")
    else:
        pass
        # logger.info("check_token_refresh: No LIVE token refresh needed")

    # oauth token
    token = get_env_key("OAUTH_TOKEN")
    expiration = int(get_env_key("OAUTH_EXPIRATION"))
    # Make sure token is not empty
    if token == "":
        authenticate()
        logger.info("check_token_refresh: Authenticated")
        return

    current_time = int(datetime.now().timestamp())
    if current_time > expiration:
        # Authentication required
        authenticate()
        logger.info("check_token_refresh: Authenticated")
        return

    elif current_time > refresh_possible_after:
        # Just refresh the token
        refresh_oauth_token()
        logger.info("check_token_refresh: Oauth token refreshed")
    else:
        pass
        # logger.info("check_token_refresh: No oauth token refresh needed")


def decode_access_token(token: str) -> tuple[int, int]:
    [_, payload, _] = token.split(".")

    # payload might need padding to be able to be decoded
    if len(payload) % 4:
        payload += "=" * (4 - len(payload) % 4)

    # decode
    decodedPayload = base64.b64decode(payload)
    jsonPayload = json.loads(decodedPayload)

    expiration = jsonPayload["exp"]
    refresh_possible_after = jsonPayload["rat"]

    return (expiration, refresh_possible_after)
