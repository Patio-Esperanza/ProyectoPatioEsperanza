import jwt
import pytest

from app.config import settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_password_no_es_texto_plano():
    hashed = hash_password("clave-secreta")
    assert hashed != "clave-secreta"
    assert verify_password("clave-secreta", hashed) is True
    assert verify_password("clave-incorrecta", hashed) is False


def test_create_access_token_contiene_claims_esperados():
    token = create_access_token("usr-1", "operador", ["patio-1"], expires_minutes=60)
    payload = decode_access_token(token)
    assert payload["sub"] == "usr-1"
    assert payload["rol"] == "operador"
    assert payload["patios"] == ["patio-1"]


def test_decode_access_token_rechaza_token_expirado():
    token = create_access_token("usr-1", "operador", [], expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_decode_access_token_rechaza_firma_invalida():
    token = create_access_token("usr-1", "operador", [], expires_minutes=60)
    tampered = token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1]
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered)
