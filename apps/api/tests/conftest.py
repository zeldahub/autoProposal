"""pytest conftest — 단위 테스트 전역 설정.

unit/ 디렉토리는 외부 시스템(DB/Mongo) 없이 import 만으로 실행 가능해야 한다.
smoke_*.py 는 별도(uvicorn 8089 필요).
"""
import sys
from pathlib import Path

# tests/unit 에서 app.* 를 import 가능하게 — apps/api 를 sys.path 에 추가
ROOT = Path(__file__).resolve().parents[1]  # apps/api
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
