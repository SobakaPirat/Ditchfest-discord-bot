import base64
import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.auth.auth import (
    authenticate,
    check_token_refresh,
    decode_access_token,
    nadeo_refresh_url,
    nadeo_url,
    oauth_url,
    refresh_access_token,
    refresh_live_access_token,
    refresh_oauth_token,
)


def make_token(exp, rat, with_padding=False):
    """Собирает JWT-подобный токен: header.payload.signature."""
    payload = base64.b64encode(json.dumps({"exp": exp, "rat": rat}).encode()).decode()
    if not with_padding:
        payload = payload.rstrip("=")
    return f"h.{payload}.s"


def make_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


@pytest.fixture
def env():
    """Мокает чтение/запись .env внутри src.auth.auth."""
    store = {
        "USER_AGENT": "test-agent",
        "UBI_LOGIN": "login",
        "UBI_PASSWORD": "pass",
        "CLIENT_ID": "cid",
        "CLIENT_SECRET": "csec",
    }
    with (
        patch("src.auth.auth.get_env_key", side_effect=lambda key: store.get(key)),
        patch("src.auth.auth.set_env_key") as mock_set,
    ):
        yield SimpleNamespace(store=store, set_key=mock_set)


@pytest.fixture
def post():
    """Мокает requests.post внутри src.auth.auth."""
    with patch("src.auth.auth.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {}
        yield mock_post


# ------------------------------------------------------------------
# decode_access_token

def test_decode_access_token_without_padding():
    token = make_token(exp=1700000000, rat=1699990000)
    assert decode_access_token(token) == (1700000000, 1699990000)


def test_decode_access_token_with_padding():
    token = make_token(exp=1700000000, rat=1699990000, with_padding=True)
    assert decode_access_token(token) == (1700000000, 1699990000)


def test_decode_access_token_invalid_token_raises():
    with pytest.raises(ValueError):
        decode_access_token("not-a-token")


# ------------------------------------------------------------------
# authenticate

def test_authenticate_saves_all_tokens(env, post):
    post.side_effect = [
        make_response({"accessToken": "nadeo_at", "refreshToken": "nadeo_rt"}),
        make_response({"accessToken": "live_at", "refreshToken": "live_rt"}),
        make_response({"access_token": "oauth_tok", "expires_in": 3600}),
    ]
    fixed_now = 1700000000
    with patch("src.auth.auth.datetime") as mock_datetime:
        mock_datetime.now.return_value.timestamp.return_value = fixed_now
        authenticate()

    # токены пишутся в .env по порядку
    assert [c.args for c in env.set_key.call_args_list] == [
        ("NADEO_ACCESS_TOKEN", "nadeo_at"),
        ("NADEO_REFRESH_TOKEN", "nadeo_rt"),
        ("NADEO_LIVESERVICES_ACCESS_TOKEN", "live_at"),
        ("NADEO_LIVESERVICES_REFRESH_TOKEN", "live_rt"),
        ("OAUTH_TOKEN", "oauth_tok"),
        ("OAUTH_EXPIRATION", str(fixed_now + 3600)),
    ]

    # первый запрос: nadeo без audience, авторизация через Ubisoft basic auth
    first = post.call_args_list[0]
    assert first.args == (nadeo_url,)
    assert first.kwargs["headers"] == {
        "Content-Type": "application/json",
        "User-Agent": "test-agent",
    }
    assert first.kwargs["auth"].username == "login"
    assert first.kwargs["auth"].password == "pass"

    # второй запрос: audience NadeoLiveServices
    second = post.call_args_list[1]
    assert second.args == (nadeo_url,)
    assert second.kwargs["json"] == {"audience": "NadeoLiveServices"}

    # третий запрос: oauth, client credentials
    third = post.call_args_list[2]
    assert third.args == (oauth_url,)
    assert third.kwargs["headers"] == {
        "content-type": "application/x-www-form-urlencoded"
    }
    assert third.kwargs["data"] == (
        "grant_type=client_credentials&client_id=cid&client_secret=csec"
    )


def test_authenticate_invalid_credentials_raises_clear_error(env, post, caplog):
    # Раньше: лог + падение по KeyError('accessToken'). Теперь — явная ошибка.
    post.return_value = make_response({"message": "invalid credentials"})
    with pytest.raises(ValueError, match="Ubisoft authentication failed"):
        authenticate()
    assert "Invalid credentials!" in caplog.text


# ------------------------------------------------------------------
# refresh_access_token

def test_refresh_access_token_saves_new_tokens(env, post):
    env.store["NADEO_REFRESH_TOKEN"] = "old_rt"
    post.return_value = make_response(
        {"accessToken": "new_at", "refreshToken": "new_rt"}
    )

    refresh_access_token()

    assert [c.args for c in env.set_key.call_args_list] == [
        ("NADEO_ACCESS_TOKEN", "new_at"),
        ("NADEO_REFRESH_TOKEN", "new_rt"),
    ]
    assert post.call_args.args == (nadeo_refresh_url,)
    assert post.call_args.kwargs["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "nadeo_v1 t=old_rt",
        "User-Agent": "test-agent",
    }


# ------------------------------------------------------------------
# refresh_live_access_token

def test_refresh_live_access_token_saves_new_tokens(env, post):
    env.store["NADEO_LIVESERVICES_REFRESH_TOKEN"] = "old_live_rt"
    post.return_value = make_response(
        {"accessToken": "live_at2", "refreshToken": "live_rt2"}
    )

    refresh_live_access_token()

    assert [c.args for c in env.set_key.call_args_list] == [
        ("NADEO_LIVESERVICES_ACCESS_TOKEN", "live_at2"),
        ("NADEO_LIVESERVICES_REFRESH_TOKEN", "live_rt2"),
    ]
    assert post.call_args.args == (nadeo_refresh_url,)
    assert post.call_args.kwargs["headers"]["Authorization"] == (
        "nadeo_v1 t=old_live_rt"
    )


def test_refresh_live_access_token_swallows_key_error(env, post):
    # Ответ без accessToken/refreshToken не должен ронять бота
    env.store["NADEO_LIVESERVICES_REFRESH_TOKEN"] = "old_live_rt"
    post.return_value = make_response({"unexpected": 1})

    refresh_live_access_token()

    env.set_key.assert_not_called()


# ------------------------------------------------------------------
# refresh_oauth_token

def test_refresh_oauth_token_saves_token_and_absolute_expiration(env, post):
    post.return_value = make_response(
        {"access_token": "new_oauth", "expires_in": 7200}
    )
    fixed_now = 1700000000
    with patch("src.auth.auth.datetime") as mock_datetime:
        mock_datetime.now.return_value.timestamp.return_value = fixed_now
        refresh_oauth_token()

    # OAUTH_EXPIRATION — абсолютная метка, как в authenticate()
    assert [c.args for c in env.set_key.call_args_list] == [
        ("OAUTH_TOKEN", "new_oauth"),
        ("OAUTH_EXPIRATION", str(fixed_now + 7200)),
    ]
    assert post.call_args.args == (oauth_url,)
    assert post.call_args.kwargs["data"] == (
        "grant_type=client_credentials&client_id=cid&client_secret=csec"
    )


def test_refresh_oauth_token_swallows_key_error(env, post):
    post.return_value = make_response({"unexpected": 1})

    refresh_oauth_token()

    env.set_key.assert_not_called()


# ------------------------------------------------------------------
# check_token_refresh

@pytest.fixture
def tokens(env):
    """Мокает внутренние функции auth'а, чтобы проверить логику решений."""
    with (
        patch("src.auth.auth.authenticate") as mock_auth,
        patch("src.auth.auth.refresh_access_token") as mock_refresh,
        patch("src.auth.auth.refresh_live_access_token") as mock_refresh_live,
        patch("src.auth.auth.refresh_oauth_token") as mock_refresh_oauth,
    ):
        yield SimpleNamespace(
            auth=mock_auth,
            refresh=mock_refresh,
            refresh_live=mock_refresh_live,
            refresh_oauth=mock_refresh_oauth,
        )


def test_check_token_refresh_noop_when_all_tokens_fresh(env, tokens):
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["OAUTH_TOKEN"] = "oauth_tok"
    env.store["OAUTH_EXPIRATION"] = str(now + 3600)

    check_token_refresh()

    tokens.auth.assert_not_called()
    tokens.refresh.assert_not_called()
    tokens.refresh_live.assert_not_called()
    tokens.refresh_oauth.assert_not_called()


def test_check_token_refresh_authenticates_when_nadeo_token_empty(env, tokens):
    env.store["NADEO_ACCESS_TOKEN"] = ""

    check_token_refresh()

    tokens.auth.assert_called_once_with()
    tokens.refresh.assert_not_called()


def test_check_token_refresh_authenticates_when_nadeo_token_expired(env, tokens):
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now - 60, now - 60)

    check_token_refresh()

    tokens.auth.assert_called_once_with()


def test_check_token_refresh_refreshes_nadeo_after_rat(env, tokens):
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now - 60)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["OAUTH_TOKEN"] = "oauth_tok"
    env.store["OAUTH_EXPIRATION"] = str(now + 3600)

    check_token_refresh()

    tokens.refresh.assert_called_once_with()
    tokens.auth.assert_not_called()


def test_check_token_refresh_authenticates_when_live_token_expired(env, tokens):
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now - 60, now - 60)
    env.store["OAUTH_TOKEN"] = "oauth_tok"
    env.store["OAUTH_EXPIRATION"] = str(now + 3600)

    check_token_refresh()

    tokens.auth.assert_called_once_with()
    tokens.refresh_live.assert_not_called()
    # Фикс: после live-expired есть return, oauth-блок не выполняется
    tokens.refresh_oauth.assert_not_called()


def test_check_token_refresh_live_rat_does_not_trigger_oauth_refresh(env, tokens):
    # Фикс: oauth-блок больше не берёт rat из live-токена (утёкшая переменная)
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now + 3600, now - 60)
    env.store["OAUTH_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["OAUTH_EXPIRATION"] = str(now + 3600)

    check_token_refresh()

    tokens.refresh_live.assert_called_once_with()
    tokens.refresh_oauth.assert_not_called()
    tokens.auth.assert_not_called()


def test_check_token_refresh_authenticates_when_oauth_expired(env, tokens):
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["OAUTH_TOKEN"] = "oauth_tok"
    env.store["OAUTH_EXPIRATION"] = str(now - 60)

    check_token_refresh()

    tokens.auth.assert_called_once_with()
    tokens.refresh_oauth.assert_not_called()


def test_check_token_refresh_authenticates_when_oauth_token_empty(env, tokens):
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["OAUTH_TOKEN"] = ""
    env.store["OAUTH_EXPIRATION"] = str(now + 3600)

    check_token_refresh()

    tokens.auth.assert_called_once_with()


def test_check_token_refresh_empty_expiration_does_not_crash(env, tokens):
    # Фикс: int(OAUTH_EXPIRATION) теперь ПОСЛЕ проверки пустого токена,
    # поэтому "" не роняет ValueError, а ведёт к authenticate().
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["OAUTH_TOKEN"] = ""
    env.store["OAUTH_EXPIRATION"] = ""

    check_token_refresh()

    tokens.auth.assert_called_once_with()


def test_check_token_refresh_missing_expiration_treats_token_as_expired(env, tokens):
    # Фикс: int(None or 0) == 0 -> токен считается протухшим -> authenticate()
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["OAUTH_TOKEN"] = "oauth_tok"

    check_token_refresh()

    tokens.auth.assert_called_once_with()


def test_check_token_refresh_refreshes_oauth_by_own_rat(env, tokens):
    # Фикс: rat берётся из самого oauth-токена
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["OAUTH_TOKEN"] = make_token(now + 3600, now - 60)
    env.store["OAUTH_EXPIRATION"] = str(now + 3600)

    check_token_refresh()

    tokens.refresh_oauth.assert_called_once_with()
    tokens.auth.assert_not_called()


def test_check_token_refresh_non_jwt_oauth_token_falls_back_to_expiration(
    env, tokens
):
    # Фикс: не-JWT oauth-токен не роняет decode, раннего обновления нет
    now = int(time.time())
    env.store["NADEO_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["NADEO_LIVESERVICES_ACCESS_TOKEN"] = make_token(now + 3600, now + 3600)
    env.store["OAUTH_TOKEN"] = "not-a-jwt"
    env.store["OAUTH_EXPIRATION"] = str(now + 3600)

    check_token_refresh()

    tokens.refresh_oauth.assert_not_called()
    tokens.auth.assert_not_called()



