"""MariaDB 마이그레이션 적용 (Flyway 대용 — 단일 PC 개발용).

사용:
  python db/init_mariadb.py          # 전체 적용 (V1, V2)
  python db/init_mariadb.py --reset  # DROP + CREATE (주의)
"""
import argparse
import os
import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "db" / "mariadb" / "migration"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=os.getenv("DB_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    p.add_argument("--user", default=os.getenv("DB_USER", "lon_app"))
    p.add_argument("--password", default=os.getenv("DB_PASSWORD", "CHANGE_ME_LON_2026"))
    p.add_argument("--database", default=os.getenv("DB_NAME", "lon"))
    p.add_argument("--reset", action="store_true")
    return p.parse_args()


def split_sql(text: str):
    """세미콜론 단위 분할 — 단순 분할 (멀티라인 statement 가정 없음)."""
    out, buf = [], []
    in_str = False
    for ch in text:
        if ch == "'":
            in_str = not in_str
        if ch == ";" and not in_str:
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
        else:
            buf.append(ch)
    rest = "".join(buf).strip()
    if rest:
        out.append(rest)
    return out


def main():
    args = parse_args()

    files = sorted(SQL_DIR.glob("V*.sql"))
    if not files:
        print(f"No SQL files in {SQL_DIR}")
        sys.exit(1)

    conn = pymysql.connect(
        host=args.host, port=args.port,
        user=args.user, password=args.password,
        database=args.database, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            if args.reset:
                cur.execute("SET FOREIGN_KEY_CHECKS=0;")
                cur.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema=%s",
                    (args.database,),
                )
                for (t,) in cur.fetchall():
                    cur.execute(f"DROP TABLE IF EXISTS `{t}`;")
                cur.execute("SET FOREIGN_KEY_CHECKS=1;")
                conn.commit()
                print(f"reset: dropped all tables in {args.database}")

            for f in files:
                print(f"apply: {f.name}")
                stmts = split_sql(f.read_text(encoding="utf-8"))
                for s in stmts:
                    cur.execute(s)
                conn.commit()
        print("OK")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
