"""
Histories API endpoints.

CRUD operations for authored historical essays with entity tagging.
"""
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text as sa_text
from typing import Optional

from app.db.session import get_db
from app.models.history import History, HistoryEntity
from app.schemas.history import (
    HistoryCreate, HistoryUpdate, HistoryResponse,
    HistoryListItem, HistoryList, HistoryEntityResponse,
)

router = APIRouter()

# Pattern to extract [name](entity:type:id) tags from body text
# Supports 6 entity types: person, event, location, shift, item, collection
# ID can be numeric (person/event/location/shift) or slug string (item/collection)
ENTITY_TAG_PATTERN = re.compile(
    r'\[([^\]]+)\]\(entity:(person|event|location|shift|item|collection):([^)]+)\)'
)


def extract_mentioned_entities(body: str) -> list[dict]:
    """Extract [name](entity:type:id) patterns from body text.

    Only person/event/location/shift are synced to history_entities
    (numeric IDs). item/collection use slug strings and are rendered
    inline but not tracked in the junction table.
    """
    mentions = []
    seen = set()
    for match in ENTITY_TAG_PATTERN.finditer(body):
        entity_type = match.group(2)
        raw_id = match.group(3)
        # Skip item/collection — slug IDs don't fit integer entity_id column
        if entity_type in ("item", "collection"):
            continue
        entity_id = int(raw_id)
        key = (entity_type, entity_id)
        if key not in seen:
            seen.add(key)
            mentions.append({
                "entity_name": match.group(1),
                "entity_type": entity_type,
                "entity_id": entity_id,
                "role": "mentioned",
            })
    return mentions


def _sync_entities(db: Session, history: History, data: HistoryCreate | HistoryUpdate, is_update: bool = False):
    """Sync history_entities from featured_entities, locations, and body mentions."""
    if is_update:
        # For updates, only sync if entities or body changed
        has_entity_changes = data.featured_entities is not None or data.locations is not None
        has_body_change = data.body is not None
        if not has_entity_changes and not has_body_change:
            return
        # Clear existing entities when re-syncing
        db.query(HistoryEntity).filter(HistoryEntity.history_id == history.id).delete()
        db.flush()

    entities_map: dict[tuple[str, int], dict] = {}

    # 1. Featured entities (highest priority)
    featured_list = data.featured_entities if data.featured_entities is not None else []
    for e in featured_list:
        key = (e.entity_type, e.entity_id)
        entities_map[key] = {
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "entity_name": e.entity_name,
            "role": "featured",
        }

    # 2. Locations
    locations_list = data.locations if data.locations is not None else []
    for loc in locations_list:
        key = ("location", loc.entity_id)
        if key not in entities_map:
            entities_map[key] = {
                "entity_type": "location",
                "entity_id": loc.entity_id,
                "entity_name": loc.entity_name,
                "role": "location",
            }

    # 3. Mentioned entities from body (lowest priority - don't override featured/location)
    body_text = data.body if data.body is not None else (history.body or "")
    for mention in extract_mentioned_entities(body_text):
        key = (mention["entity_type"], mention["entity_id"])
        if key not in entities_map:
            entities_map[key] = mention

    # Insert all entities
    for entity_data in entities_map.values():
        he = HistoryEntity(
            history_id=history.id,
            entity_type=entity_data["entity_type"],
            entity_id=entity_data["entity_id"],
            entity_name=entity_data.get("entity_name"),
            role=entity_data["role"],
        )
        db.add(he)


@router.get("", response_model=HistoryList)
async def list_histories(
    category: Optional[str] = Query(None, description="Filter by category"),
    era_start: Optional[int] = Query(None, description="Filter: era starts after"),
    era_end: Optional[int] = Query(None, description="Filter: era ends before"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    status: Optional[str] = Query(None, description="Filter by status"),
    author_type: Optional[str] = Query(None, description="Filter by author_type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (person, event, location)"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List histories with optional filtering."""
    query = db.query(History)

    # Entity filtering via history_entities junction table
    if entity_type and entity_id is not None:
        query = query.join(HistoryEntity, History.id == HistoryEntity.history_id).filter(
            HistoryEntity.entity_type == entity_type,
            HistoryEntity.entity_id == entity_id,
        )
    elif entity_type:
        query = query.join(HistoryEntity, History.id == HistoryEntity.history_id).filter(
            HistoryEntity.entity_type == entity_type,
        )

    if category:
        query = query.filter(History.category == category)
    if status:
        query = query.filter(History.status == status)
    else:
        query = query.filter(History.status != "archived")
    if author_type:
        query = query.filter(History.author_type == author_type)
    if era_start is not None:
        query = query.filter(History.era_end >= era_start)
    if era_end is not None:
        query = query.filter(History.era_start <= era_end)
    if tag:
        query = query.filter(History.tags.any(tag))

    total = query.count()
    histories = (
        query
        .order_by(History.importance.desc(), History.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Get entity counts in batch
    history_ids = [h.id for h in histories]
    entity_counts: dict[int, int] = {}
    if history_ids:
        rows = db.execute(sa_text("""
            SELECT history_id, COUNT(*) as cnt
            FROM history_entities
            WHERE history_id = ANY(:ids)
            GROUP BY history_id
        """), {"ids": history_ids})
        for row in rows:
            entity_counts[row[0]] = row[1]

    items = []
    for h in histories:
        items.append(HistoryListItem(
            id=h.id,
            title=h.title,
            title_ko=h.title_ko,
            summary=h.summary,
            era_start=h.era_start,
            era_end=h.era_end,
            category=h.category or "essay",
            author_type=h.author_type or "system",
            author_name=h.author_name,
            importance=h.importance or 3,
            status=h.status or "published",
            entity_count=entity_counts.get(h.id, 0),
            created_at=h.created_at,
        ))

    return HistoryList(items=items, total=total)


@router.get("/{history_id}", response_model=HistoryResponse)
async def get_history(
    history_id: int,
    db: Session = Depends(get_db),
):
    """Get a history with all its entities."""
    history = (
        db.query(History)
        .options(joinedload(History.entities))
        .filter(History.id == history_id)
        .first()
    )
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    return history


@router.post("", response_model=HistoryResponse)
async def create_history(
    data: HistoryCreate,
    db: Session = Depends(get_db),
):
    """Create a new history. Entity tags in body are auto-parsed."""
    history = History(
        title=data.title,
        title_ko=data.title_ko,
        title_ja=data.title_ja,
        summary=data.summary,
        era_start=data.era_start,
        era_end=data.era_end,
        body=data.body,
        body_ko=data.body_ko,
        body_ja=data.body_ja,
        category=data.category,
        tags=data.tags,
        author_type=data.author_type,
        author_name=data.author_name,
        importance=data.importance,
    )
    db.add(history)
    db.flush()  # Get the ID

    _sync_entities(db, history, data)
    db.commit()
    db.refresh(history)

    # Reload with entities
    history = (
        db.query(History)
        .options(joinedload(History.entities))
        .filter(History.id == history.id)
        .first()
    )
    return history


@router.put("/{history_id}", response_model=HistoryResponse)
async def update_history(
    history_id: int,
    data: HistoryUpdate,
    db: Session = Depends(get_db),
):
    """Update a history. Entity tags in body are re-parsed."""
    history = db.query(History).filter(History.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")

    # Update scalar fields
    update_fields = data.model_dump(exclude_unset=True, exclude={"featured_entities", "locations"})
    for field, value in update_fields.items():
        setattr(history, field, value)
    history.updated_at = datetime.utcnow()

    db.flush()

    _sync_entities(db, history, data, is_update=True)
    db.commit()

    # Reload with entities
    history = (
        db.query(History)
        .options(joinedload(History.entities))
        .filter(History.id == history_id)
        .first()
    )
    return history


@router.delete("/{history_id}")
async def delete_history(
    history_id: int,
    db: Session = Depends(get_db),
):
    """Delete a history and its entity links."""
    history = db.query(History).filter(History.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History not found")

    db.delete(history)
    db.commit()
    return {"detail": "History deleted", "id": history_id}
