"""
Signing in with a bearer token, end to end: a good token gets you in, anything
else is a 401 on protected routes and plain anonymous access on public ones.
"""
import time

import pytest

from tests.conftest import auth_headers
from tests.unit.test_access_tokens import hand_made_token


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user(make_user):
    return make_user(email="member@example.com")


def test_issued_token_signs_the_user_in(client, user):
    response = client.get("/users/me", headers=auth_headers(user))

    assert response.status_code == 200, response.text
    assert response.json()["email"] == "member@example.com"


def test_token_from_before_the_library_swap_still_works(client, user):
    token = hand_made_token({"sub": user.email, "exp": int(time.time()) + 600})

    assert client.get("/users/me", headers=bearer(token)).status_code == 200


@pytest.mark.parametrize("claims, secret", [
    ({"sub": "member@example.com", "exp": int(time.time()) - 60}, None),             # expired
    ({"sub": "member@example.com", "exp": int(time.time()) + 600}, "wrong-secret"),  # forged
    ({"exp": int(time.time()) + 600}, None),                                         # no subject
    ({"sub": "nobody@example.com", "exp": int(time.time()) + 600}, None),            # unknown user
])
def test_bad_tokens_are_401(client, user, claims, secret):
    response = client.get("/users/me", headers=bearer(hand_made_token(claims, secret)))

    assert response.status_code == 401
    assert response.json()["detail"]


def test_garbage_and_missing_tokens_are_401(client, user):
    assert client.get("/users/me", headers=bearer("not.a.token")).status_code == 401
    assert client.get("/users/me", headers=bearer("garbage")).status_code == 401
    assert client.get("/users/me").status_code == 401


def test_public_route_treats_a_bad_token_as_anonymous(client, user, make_event):
    make_event()
    expired = hand_made_token({"sub": user.email, "exp": int(time.time()) - 60})

    anonymous = client.get("/events")
    with_bad_token = client.get("/events", headers=bearer(expired))

    assert anonymous.status_code == 200
    assert with_bad_token.status_code == 200
    assert with_bad_token.json() == anonymous.json()
