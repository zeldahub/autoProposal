"""JWT + AES-256-GCM (API Key 암호화)."""
import base64
import os
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def create_access_token(sub: str, ttl_min: int = 15) -> str:
    payload = {
        "sub": sub,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=ttl_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def _master_key() -> bytes:
    if settings.aes_master_key_b64:
        return base64.b64decode(settings.aes_master_key_b64)
    # 개발용 — 운영에서는 반드시 환경변수 설정
    return b"dev-only-aes-master-key-32bytes!"[:32]


def encrypt_secret(plain: str) -> tuple[bytes, bytes, bytes]:
    aes = AESGCM(_master_key())
    iv = os.urandom(12)
    ct_with_tag = aes.encrypt(iv, plain.encode("utf-8"), None)
    # AESGCM은 tag를 ct 끝에 붙임 (16바이트)
    cipher, tag = ct_with_tag[:-16], ct_with_tag[-16:]
    return cipher, iv, tag


def decrypt_secret(cipher: bytes, iv: bytes, tag: bytes) -> str:
    aes = AESGCM(_master_key())
    return aes.decrypt(iv, cipher + tag, None).decode("utf-8")
