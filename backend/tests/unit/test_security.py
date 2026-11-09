from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_roundtrip_and_salting():
    h1, h2 = hash_password("S3cret-pass"), hash_password("S3cret-pass")
    assert h1 != h2                       # salted
    assert verify_password("S3cret-pass", h1)
    assert not verify_password("wrong", h1)


def test_overlong_password_rejected():
    with pytest.raises(ValueError):
        hash_password("x" * 73)
    assert not verify_password("x" * 73, hash_password("ok"))


def test_malformed_hash_does_not_raise():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_token_roundtrip():
    claims = decode_access_token(create_access_token("user-1", "investigator"))
    assert claims["sub"] == "user-1" and claims["role"] == "investigator"


def test_expired_token_rejected():
    token = create_access_token("u", "analyst", expires_delta=timedelta(seconds=-5))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_token_rejected():
    token = create_access_token("u", "analyst")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token[:-2] + ("AA" if token[-2:] != "AA" else "BB"))
