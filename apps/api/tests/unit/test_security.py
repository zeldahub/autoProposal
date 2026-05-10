"""core/security — JWT + AES-GCM 단위 테스트."""
import pytest

from app.core.security import (
    create_access_token, decode_token,
    encrypt_secret, decrypt_secret,
)


class TestJwt:
    def test_round_trip(self):
        tok = create_access_token("user-uuid-1", ttl_min=10)
        decoded = decode_token(tok)
        assert decoded["sub"] == "user-uuid-1"
        assert "exp" in decoded and "iat" in decoded

    def test_expired(self):
        import jwt
        # ttl_min=-1 → 이미 만료
        tok = create_access_token("expired", ttl_min=-1)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(tok)

    def test_tampered_signature(self):
        import jwt
        tok = create_access_token("u")
        # 마지막 바이트 변경
        bad = tok[:-1] + ("A" if tok[-1] != "A" else "B")
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(bad)


class TestAesGcm:
    def test_round_trip_ascii(self):
        cipher, iv, tag = encrypt_secret("sk-test-1234")
        assert isinstance(cipher, bytes) and isinstance(iv, bytes) and isinstance(tag, bytes)
        assert len(iv) == 12 and len(tag) == 16
        assert decrypt_secret(cipher, iv, tag) == "sk-test-1234"

    def test_round_trip_korean(self):
        plain = "한국어 비밀키 테스트 — 한자/특수문자 #@$%"
        c, i, t = encrypt_secret(plain)
        assert decrypt_secret(c, i, t) == plain

    def test_iv_unique_per_encrypt(self):
        ivs = {encrypt_secret("same-plaintext")[1] for _ in range(20)}
        assert len(ivs) == 20  # IV 충돌 없음

    def test_tampered_ciphertext_fails(self):
        from cryptography.exceptions import InvalidTag
        c, i, t = encrypt_secret("plain")
        bad = bytes([c[0] ^ 1]) + c[1:] if c else b"\x00"
        with pytest.raises(InvalidTag):
            decrypt_secret(bad, i, t)

    def test_tampered_tag_fails(self):
        from cryptography.exceptions import InvalidTag
        c, i, t = encrypt_secret("plain")
        bad_tag = bytes([t[0] ^ 1]) + t[1:]
        with pytest.raises(InvalidTag):
            decrypt_secret(c, i, bad_tag)
