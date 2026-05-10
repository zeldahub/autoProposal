"""CAT-01 — 표준 목차 트리 (실 DB) + locale 필터."""
from fastapi import APIRouter, Query

from app.core.deps import DbDep
from app.models import ProposalCategory

router = APIRouter()


@router.get("")
async def list_categories(db: DbDep, locale: str = Query(default="ko", pattern="^(ko|en)$")):
    rows = (
        db.query(ProposalCategory)
        .filter(ProposalCategory.is_active == 1)
        .order_by(ProposalCategory.sort_order)
        .all()
    )
    items = []
    for r in rows:
        if locale == "en":
            name = r.name_en or r.name_ko
        else:
            name = r.name_ko
        items.append({
            "code": r.code,
            "name": name,
            "nameKo": r.name_ko,
            "nameEn": r.name_en,
            "sort": r.sort_order,
        })
    return {"data": {"items": items}, "error": None, "traceId": ""}
