"""
Showcase API - Legacy endpoints backed by portal_items DB table.

Original JSON-file-based endpoints are preserved for backward compatibility.
All data now comes from the portal_items table (seeded from the same JSONs).

Fallback: If DB is empty, loads from JSON files directly.
"""
import json
from pathlib import Path
from typing import List, Optional, Literal
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.v2.portal import PortalItem

router = APIRouter()

# Fallback data directory (used only if DB is empty)
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "showcases"


# === Pydantic Models (unchanged for backward compat) ===

class RelatedServant(BaseModel):
    name: str
    class_: str

    class Config:
        populate_by_name = True

    @classmethod
    def from_dict(cls, data: dict):
        return cls(name=data.get("name", ""), class_=data.get("class", ""))


class Section(BaseModel):
    title: str
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    content: str
    content_ko: Optional[str] = None
    content_ja: Optional[str] = None


class ShowcaseItem(BaseModel):
    id: str
    type: Literal["singularity", "lostbelt", "servant", "article"]
    title: str
    title_ko: Optional[str] = None
    title_ja: Optional[str] = None
    subtitle: Optional[str] = None
    subtitle_ko: Optional[str] = None
    subtitle_ja: Optional[str] = None
    chapter: Optional[str] = None
    era: Optional[str] = None
    year: Optional[int] = None
    location: Optional[str] = None
    description: str
    description_ko: Optional[str] = None
    description_ja: Optional[str] = None
    sections: List[Section] = []
    historical_basis: Optional[str] = None
    historical_basis_ko: Optional[str] = None
    historical_basis_ja: Optional[str] = None
    related_servants: List[RelatedServant] = []
    related_event_ids: List[int] = []
    sources: List[str] = []


class ShowcaseListResponse(BaseModel):
    items: List[ShowcaseItem]
    total: int
    category: str


# === DB → ShowcaseItem conversion ===

# Map DB item_type back to legacy 'type' field
LEGACY_TYPE_MAP = {
    "singularity": "singularity",
    "lostbelt": "lostbelt",
    "servant_column": "servant",
    "history": "article",
    "literature": "article",
    "music": "article",
    "essay": "article",
}


def portal_item_to_showcase(item: PortalItem) -> ShowcaseItem:
    """Convert a PortalItem ORM object to legacy ShowcaseItem."""
    sections = [Section(**s) for s in (item.sections or [])]
    servants = [RelatedServant.from_dict(s) for s in (item.related_servants or [])]

    return ShowcaseItem(
        id=item.slug,
        type=LEGACY_TYPE_MAP.get(item.item_type, "article"),
        title=item.title,
        title_ko=item.title_ko,
        title_ja=item.title_ja,
        subtitle=item.subtitle,
        subtitle_ko=item.subtitle_ko,
        subtitle_ja=item.subtitle_ja,
        chapter=item.chapter,
        era=item.era,
        year=item.year,
        location=item.location,
        description=item.description,
        description_ko=item.description_ko,
        description_ja=item.description_ja,
        sections=sections,
        historical_basis=item.historical_basis,
        historical_basis_ko=item.historical_basis_ko,
        historical_basis_ja=item.historical_basis_ja,
        related_servants=servants,
        related_event_ids=item.related_event_ids or [],
        sources=item.sources or [],
    )


def _query_items_by_type(db: Session, *item_types: str) -> List[ShowcaseItem]:
    """Query portal_items by type(s), with JSON fallback."""
    items = (
        db.query(PortalItem)
        .filter(PortalItem.item_type.in_(item_types))
        .order_by(PortalItem.sort_order, PortalItem.id)
        .all()
    )
    if items:
        return [portal_item_to_showcase(i) for i in items]

    # Fallback: load from JSON
    return _load_json_fallback(item_types)


def _load_json_fallback(item_types: tuple) -> List[ShowcaseItem]:
    """Load from JSON files as fallback when DB is empty."""
    type_to_file = {
        "singularity": "singularities.json",
        "lostbelt": "lostbelts.json",
        "servant_column": "servants.json",
        "history": "history.json",
        "literature": "literature.json",
        "music": "music.json",
    }
    all_items = []
    for t in item_types:
        filename = type_to_file.get(t)
        if not filename:
            continue
        filepath = DATA_DIR / filename
        if not filepath.exists():
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            raw_items = json.load(f)
        for raw in raw_items:
            sections = [Section(**s) for s in raw.get("sections", [])]
            servants = [RelatedServant.from_dict(s) for s in raw.get("related_servants", [])]
            all_items.append(ShowcaseItem(
                id=raw["id"], type=raw["type"],
                title=raw["title"], title_ko=raw.get("title_ko"), title_ja=raw.get("title_ja"),
                subtitle=raw.get("subtitle"), subtitle_ko=raw.get("subtitle_ko"), subtitle_ja=raw.get("subtitle_ja"),
                chapter=raw.get("chapter"), era=raw.get("era"), year=raw.get("year"), location=raw.get("location"),
                description=raw["description"], description_ko=raw.get("description_ko"), description_ja=raw.get("description_ja"),
                sections=sections,
                historical_basis=raw.get("historical_basis"), historical_basis_ko=raw.get("historical_basis_ko"), historical_basis_ja=raw.get("historical_basis_ja"),
                related_servants=servants, related_event_ids=raw.get("related_event_ids", []), sources=raw.get("sources", []),
            ))
    return all_items


# === FGO Content ===

@router.get("/fgo/singularities", response_model=ShowcaseListResponse)
def list_singularities(db: Session = Depends(get_db)):
    items = _query_items_by_type(db, "singularity")
    return ShowcaseListResponse(items=items, total=len(items), category="singularity")


@router.get("/fgo/lostbelts", response_model=ShowcaseListResponse)
def list_lostbelts(db: Session = Depends(get_db)):
    items = _query_items_by_type(db, "lostbelt")
    return ShowcaseListResponse(items=items, total=len(items), category="lostbelt")


@router.get("/fgo/servants", response_model=ShowcaseListResponse)
def list_servant_articles(db: Session = Depends(get_db)):
    items = _query_items_by_type(db, "servant_column")
    return ShowcaseListResponse(items=items, total=len(items), category="servant")


# === Pan-Human History ===

@router.get("/history", response_model=ShowcaseListResponse)
def list_history_articles(db: Session = Depends(get_db)):
    items = _query_items_by_type(db, "history")
    return ShowcaseListResponse(items=items, total=len(items), category="history")


@router.get("/literature", response_model=ShowcaseListResponse)
def list_literature_articles(db: Session = Depends(get_db)):
    items = _query_items_by_type(db, "literature")
    return ShowcaseListResponse(items=items, total=len(items), category="literature")


@router.get("/music", response_model=ShowcaseListResponse)
def list_music_articles(db: Session = Depends(get_db)):
    items = _query_items_by_type(db, "music")
    return ShowcaseListResponse(items=items, total=len(items), category="music")


# === Generic Endpoints ===

@router.get("/", response_model=ShowcaseListResponse)
def list_all_showcases(
    type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    all_types = ("singularity", "lostbelt", "servant_column", "history", "literature", "music")
    all_items = _query_items_by_type(db, *all_types)

    if type:
        legacy_to_db = {"servant": "servant_column", "article": None}
        db_type = legacy_to_db.get(type, type)
        if db_type:
            all_items = [i for i in all_items if LEGACY_TYPE_MAP.get(db_type) == i.type or i.type == type]
        else:
            all_items = [i for i in all_items if i.type == type]

    total = len(all_items)
    items = all_items[offset:offset + limit]
    return ShowcaseListResponse(items=items, total=total, category="all")


@router.get("/{showcase_id}", response_model=ShowcaseItem)
def get_showcase_by_id(showcase_id: str, db: Session = Depends(get_db)):
    item = db.query(PortalItem).filter(PortalItem.slug == showcase_id).first()
    if item:
        return portal_item_to_showcase(item)

    # Fallback to JSON
    all_types = ("singularity", "lostbelt", "servant_column", "history", "literature", "music")
    all_items = _load_json_fallback(all_types)
    for i in all_items:
        if i.id == showcase_id:
            return i

    raise HTTPException(status_code=404, detail=f"Showcase '{showcase_id}' not found")


# === Stats ===

@router.get("/stats/summary")
def get_showcase_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    counts = (
        db.query(PortalItem.item_type, func.count(PortalItem.id))
        .group_by(PortalItem.item_type)
        .all()
    )
    count_map = dict(counts)

    if not count_map:
        # Fallback
        return {
            "fgo": {
                "singularities": len(_load_json_fallback(("singularity",))),
                "lostbelts": len(_load_json_fallback(("lostbelt",))),
                "servants": len(_load_json_fallback(("servant_column",))),
            },
            "pan_human_history": {
                "history": len(_load_json_fallback(("history",))),
                "literature": len(_load_json_fallback(("literature",))),
                "music": len(_load_json_fallback(("music",))),
            }
        }

    return {
        "fgo": {
            "singularities": count_map.get("singularity", 0),
            "lostbelts": count_map.get("lostbelt", 0),
            "servants": count_map.get("servant_column", 0),
        },
        "pan_human_history": {
            "history": count_map.get("history", 0),
            "literature": count_map.get("literature", 0),
            "music": count_map.get("music", 0),
        }
    }
