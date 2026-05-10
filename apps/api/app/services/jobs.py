"""APScheduler 백그라운드 잡 — 첨부 정리, Mongo 고아 정리.

- AsyncIOScheduler 사용 (FastAPI 이벤트 루프 공유)
- in-memory job history (최근 20건)
- 모든 잡은 register_jobs() 에서 등록, lifespan 에서 start/shutdown
"""
import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from bson import ObjectId

from app.core.config import settings
from app.core.db_maria import get_session_factory
from app.core.db_mongo import get_mongo_db
from app.models import Project, ProjectAttachment

logger = logging.getLogger("lon.jobs")

scheduler = AsyncIOScheduler(timezone="UTC")
_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))


@dataclass
class JobRunRecord:
    at: str
    status: str  # OK | ERROR | RUNNING
    durationMs: int | None = None
    result: dict | None = None
    error: str | None = None


# ── Job 정의 ────────────────────────────────────────────────────────
@dataclass
class JobDef:
    id: str
    label: str
    description: str
    interval_min: int
    fn: Callable[[], Awaitable[dict]]


async def cleanup_attachments() -> dict:
    """첨부 파일 24h(default) 이상 경과분 정리. 산출물(artifact)은 보존."""
    cutoff = datetime.now(UTC) - timedelta(hours=settings.attachment_ttl_hours)
    deleted = 0
    bytes_freed = 0
    SessionLocal = get_session_factory()
    db = SessionLocal()
    mongo = get_mongo_db()
    try:
        rows = (
            db.query(ProjectAttachment)
            .filter(ProjectAttachment.created_at < cutoff.replace(tzinfo=None))
            .all()
        )
        for a in rows:
            try:
                p = Path(a.storage_path)
                if p.exists():
                    bytes_freed += p.stat().st_size
                    p.unlink(missing_ok=True)
            except Exception as e:  # noqa: BLE001
                logger.warning("FS unlink fail %s: %s", a.storage_path, e)
            if a.mongo_doc_id:
                try:
                    mongo["documents"].delete_one({"_id": ObjectId(a.mongo_doc_id)})
                except Exception as e:  # noqa: BLE001
                    logger.warning("mongo delete fail %s: %s", a.mongo_doc_id, e)
            db.delete(a)
            deleted += 1
        db.commit()
    finally:
        db.close()
    return {"deleted": deleted, "bytesFreed": bytes_freed, "cutoff": cutoff.isoformat()}


async def repair_mongo() -> dict:
    """Mongo documents 중 MariaDB 의 project 가 더 이상 없는 고아 항목 삭제."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    mongo = get_mongo_db()
    try:
        valid = {p.uuid for p in db.query(Project.uuid).all()}
    finally:
        db.close()

    coll_names = ["documents", "analysisResults", "llmSessions", "proposalDrafts", "wbsTasks"]
    removed: dict[str, int] = {}
    for c in coll_names:
        # 큰 컬렉션 보호: project_uuid 가 없는 행만 본다
        cursor = mongo[c].find({"projectUuid": {"$exists": True}}, {"projectUuid": 1})
        ids_to_remove = [doc["_id"] for doc in cursor if doc.get("projectUuid") not in valid]
        if ids_to_remove:
            res = mongo[c].delete_many({"_id": {"$in": ids_to_remove}})
            removed[c] = res.deleted_count
        else:
            removed[c] = 0
    return {"removed": removed, "validProjects": len(valid)}


JOB_DEFS: list[JobDef] = [
    JobDef(
        id="attachment-cleanup",
        label="첨부 24h 정리",
        description=f"created_at 가 {settings.attachment_ttl_hours}h 이전인 첨부 파일·Mongo documents 삭제",
        interval_min=settings.attachment_cleanup_interval_min,
        fn=cleanup_attachments,
    ),
    JobDef(
        id="mongo-repair",
        label="Mongo 고아 정리",
        description="MariaDB 에 더 이상 없는 project 의 Mongo 컬렉션 행 삭제",
        interval_min=settings.mongo_repair_interval_min,
        fn=repair_mongo,
    ),
]


def _notify_admins_about(job_id: str, label: str, rec: JobRunRecord) -> None:
    """잡 결과를 ADMIN 들에게 알림 — 에러는 항상, 성공은 의미있는 결과(있을 때)만."""
    from app.services.notify import notify_admins  # 지연 임포트로 순환 의존 회피

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        if rec.status == "ERROR":
            notify_admins(
                db, type="JOB", level="ERROR",
                title=f"[잡 실패] {label}",
                message=rec.error or "원인 미상",
                link="/admin/jobs",
                meta={"jobId": job_id, "durationMs": rec.durationMs},
                commit=True,
            )
        elif rec.status == "OK" and rec.result:
            # 의미있는 결과(파일 정리, 고아 정리)만 알림
            r = rec.result
            interesting = bool(
                r.get("deleted") or r.get("bytesFreed")
                or any((r.get("removed") or {}).values())
            )
            if interesting:
                notify_admins(
                    db, type="JOB", level="SUCCESS",
                    title=f"[잡 완료] {label}",
                    message=_summarize_result(r),
                    link="/admin/jobs",
                    meta={"jobId": job_id, "durationMs": rec.durationMs, "result": r},
                    commit=True,
                )
    except Exception as e:  # noqa: BLE001
        logger.warning("notify_admins for job %s failed: %s", job_id, e)
    finally:
        db.close()


def _summarize_result(r: dict) -> str:
    parts = []
    if r.get("deleted"):
        parts.append(f"정리 {r['deleted']}건")
    if r.get("bytesFreed"):
        parts.append(f"{r['bytesFreed']:,} bytes 회수")
    if r.get("removed"):
        rm_total = sum((r.get("removed") or {}).values())
        if rm_total:
            parts.append(f"고아 문서 {rm_total}건 제거")
    return " · ".join(parts) if parts else "변경 없음"


def _wrap(job_id: str, fn: Callable[[], Awaitable[dict]]):
    async def runner():
        running = JobRunRecord(at=datetime.now(UTC).isoformat(), status="RUNNING")
        _history[job_id].append(running)
        t0 = time.time()
        try:
            result = await fn()
            rec = JobRunRecord(
                at=running.at, status="OK",
                durationMs=int((time.time() - t0) * 1000),
                result=result,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("job %s failed", job_id)
            rec = JobRunRecord(
                at=running.at, status="ERROR",
                durationMs=int((time.time() - t0) * 1000),
                error=str(e)[:300],
            )
        # in-place 업데이트 (마지막 추가된 항목 교체)
        if _history[job_id] and _history[job_id][-1].status == "RUNNING":
            _history[job_id][-1] = rec
        else:
            _history[job_id].append(rec)
        # 관리자 알림 (실패 항상, 성공은 의미있는 결과만)
        label = next((d.label for d in JOB_DEFS if d.id == job_id), job_id)
        _notify_admins_about(job_id, label, rec)
    return runner


def register_jobs():
    if not settings.jobs_enabled:
        logger.info("jobs disabled via JOBS_ENABLED=false")
        return
    for d in JOB_DEFS:
        scheduler.add_job(
            _wrap(d.id, d.fn),
            trigger=IntervalTrigger(minutes=d.interval_min),
            id=d.id,
            replace_existing=True,
            next_run_time=datetime.now(UTC) + timedelta(seconds=30),  # 부팅 직후 30초
            max_instances=1,
            coalesce=True,
        )
    logger.info("registered %d jobs", len(JOB_DEFS))


def list_jobs_view() -> list[dict]:
    """관리자 화면용 직렬화."""
    out = []
    by_id = {j.id: j for j in scheduler.get_jobs()}
    for d in JOB_DEFS:
        sj = by_id.get(d.id)
        out.append({
            "id": d.id,
            "label": d.label,
            "description": d.description,
            "intervalMin": d.interval_min,
            "nextRunAt": sj.next_run_time.isoformat() if (sj and sj.next_run_time) else None,
            "paused": (sj is not None and sj.next_run_time is None),
            "history": [asdict(r) for r in list(_history.get(d.id, []))[::-1]],
        })
    return out


async def run_job_now(job_id: str) -> dict:
    """즉시 실행 — coroutine 직접 호출 (스케줄러 큐 우회로 결과 즉시 확인)."""
    found = next((d for d in JOB_DEFS if d.id == job_id), None)
    if not found:
        raise KeyError(job_id)
    runner = _wrap(found.id, found.fn)
    await runner()
    last = _history[job_id][-1] if _history[job_id] else None
    return asdict(last) if last else {"status": "UNKNOWN"}


def pause(job_id: str) -> bool:
    j = scheduler.get_job(job_id)
    if not j:
        return False
    scheduler.pause_job(job_id)
    return True


def resume(job_id: str) -> bool:
    j = scheduler.get_job(job_id)
    if not j:
        return False
    scheduler.resume_job(job_id)
    return True


def shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)
