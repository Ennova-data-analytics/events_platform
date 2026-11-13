"""
Access tokens are plain HS256 JWTs. They have to stay readable by anything that
speaks the standard, so tokens already sitting in people's browsers keep
working when the JWT library is swapped (python-jose -> PyJWT).
"""
import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest

from core.config import settings
from core.security import create_access_token


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def hand_made_token(claims: dict, secret: str | None = None) -> str:
    """An HS256 token built with nothing but the standard library."""
    secret = settings.SECRET_KEY if secret is None else secret
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps(claims, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{b64(signature)}"


def decode(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def test_token_is_a_string_carrying_the_subject_and_an_expiry():
    token = create_access_token({"sub": "someone@example.com"})

    assert isinstance(token, str) and token.count(".") == 2
    claims = decode(token)
    assert claims["sub"] == "someone@example.com"
    lifetime = claims["exp"] - time.time()
    assert 0 < lifetime <= settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_token_has_a_standard_hs256_signature():
    token = create_access_token({"sub": "someone@example.com"})
    signed, signature = token.rsplit(".", 1)

    expected = hmac.new(settings.SECRET_KEY.encode(), signed.encode(), hashlib.sha256).digest()
    assert signature == b64(expected)


def test_token_from_another_standard_issuer_is_accepted():
    token = hand_made_token({"sub": "someone@example.com", "exp": int(time.time()) + 60})

    assert decode(token)["sub"] == "someone@example.com"


def test_expired_token_is_refused():
    with pytest.raises(jwt.ExpiredSignatureError):
        decode(hand_made_token({"sub": "someone@example.com", "exp": int(time.time()) - 60}))


def test_token_signed_with_another_secret_is_refused():
    token = hand_made_token({"sub": "someone@example.com", "exp": int(time.time()) + 60}, secret="not-the-secret")

    with pytest.raises(jwt.InvalidSignatureError):
        decode(token)


def test_unsigned_token_is_refused():
    head = b64(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    body = b64(json.dumps({"sub": "someone@example.com", "exp": int(time.time()) + 60}).encode())

    with pytest.raises(jwt.InvalidTokenError):
        decode(f"{head}.{body}.")


def test_original_claims_arent_mutated():
    claims = {"sub": "someone@example.com"}
    create_access_token(claims)

    assert claims == {"sub": "someone@example.com"}
