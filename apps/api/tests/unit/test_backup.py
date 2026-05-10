"""backup 서비스 — _safe_name 등 헬퍼 단위 테스트."""
from app.services.backup import _safe_name


class TestSafeName:
    def test_alphanumeric(self):
        assert _safe_name("abc123") == "abc123"

    def test_korean_replaced(self):
        # 한글은 alnum 이지만 isalnum() 은 True. 실제 동작 확인
        assert _safe_name("한글파일.txt") == "한글파일.txt"

    def test_special_chars_replaced(self):
        assert _safe_name("foo/bar*baz?.zip") == "foo_bar_baz_.zip"

    def test_long_truncated(self):
        long = "a" * 200
        assert len(_safe_name(long)) <= 120

    def test_underscore_kept(self):
        assert _safe_name("foo_bar.zip") == "foo_bar.zip"
