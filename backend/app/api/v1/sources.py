"""
Sources API endpoints.

Provides:
- List sources (books, documents)
- Source details
- Persons mentioned in a source
- Mentions with context
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.schemas.source import (
    SourceList,
    SourceSummary,
    SourceDetail,
    SourcePersonList,
    SourcePersonSummary,
)
from app.services import source_service

router = APIRouter()


@router.get("", response_model=SourceList)
async def list_sources(
    type: Optional[str] = Query(None, description="Filter by type (gutenberg, wikipedia, etc.)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List sources (books, documents) with mention statistics.

    Sources are ordered by total mention count.
    Only sources with at least one text mention are returned.

    Types:
    - gutenberg: Project Gutenberg books
    - wikipedia: Wikipedia articles
    - document: General documents
    - digital_archive: Digital archive entries
    """
    items, total = source_service.get_sources(
        db,
        source_type=type,
        limit=limit,
        offset=offset,
    )

    return SourceList(
        items=[SourceSummary(**item) for item in items],
        total=total
    )


@router.get("/{source_id}", response_model=SourceDetail)
async def get_source(
    source_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a source.

    Includes:
    - Basic metadata (title, author, year)
    - Mention statistics by entity type
    """
    source = source_service.get_source_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    return SourceDetail(**source)


@router.get("/{source_id}/persons", response_model=SourcePersonList)
async def get_source_persons(
    source_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    min_mentions: int = Query(1, ge=1, description="Minimum mention count to include"),
    db: Session = Depends(get_db),
):
    """
    Get historical figures mentioned in a source.

    Returns persons ordered by mention count.
    Use min_mentions to filter out minor mentions.
    """
    # Verify source exists
    source = source_service.get_source_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    persons, total = source_service.get_source_persons(
        db,
        source_id=source_id,
        limit=limit,
        offset=offset,
        min_mentions=min_mentions,
    )

    return SourcePersonList(
        source_id=source_id,
        persons=[SourcePersonSummary(**p) for p in persons],
        total=total
    )


@router.get("/{source_id}/mentions")
async def get_source_mentions(
    source_id: int,
    entity_type: Optional[str] = Query(None, description="Filter by entity type (person, location, event)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get all entity mentions in a source with context.

    Returns mentions ordered by position in document (chunk_index).
    Includes the actual mention text and surrounding context.
    """
    # Verify source exists
    source = source_service.get_source_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    mentions, total = source_service.get_source_mentions(
        db,
        source_id=source_id,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )

    return {
        "source_id": source_id,
        "mentions": mentions,
        "total": total
    }


@router.get("/wiki/{source_id}")
async def get_wikipedia_content(
    source_id: int,
    db: Session = Depends(get_db),
):
    """
    Get Wikipedia article content from local ZIM file.

    Fetches the full article from the local Wikipedia ZIM archive.
    Returns HTML and plain text content.
    """
    from pathlib import Path
    from sqlalchemy import text

    # Get source info
    source = db.execute(text('''
        SELECT wikidata_id, title FROM sources WHERE id = :id
    '''), {"id": source_id}).fetchone()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    wikidata_id = source[0]
    title = source[1]

    # Extract Wikipedia title from source title (remove " - Wikidata" suffix)
    wiki_title = title.replace(" - Wikidata", "").strip() if title else None

    if not wiki_title:
        raise HTTPException(status_code=404, detail="No Wikipedia title found")

    # Try to load from ZIM
    ZIM_PATH = Path("E:/chaldeas_data/kiwix/wikipedia_en_nopic.zim")

    if not ZIM_PATH.exists():
        # Return wikidata URL as fallback
        return {
            "source_id": source_id,
            "title": wiki_title,
            "content_html": None,
            "content_text": None,
            "external_url": f"https://en.wikipedia.org/wiki/{wiki_title.replace(' ', '_')}",
            "status": "zim_not_found"
        }

    try:
        from libzim.reader import Archive
        from bs4 import BeautifulSoup

        zim = Archive(str(ZIM_PATH))

        # Try different path formats
        paths = [
            f"A/{wiki_title.replace(' ', '_')}",
            f"{wiki_title.replace(' ', '_')}",
        ]

        entry = None
        for path in paths:
            try:
                entry = zim.get_entry_by_path(path)
                break
            except:
                continue

        if not entry:
            return {
                "source_id": source_id,
                "title": wiki_title,
                "content_html": None,
                "content_text": None,
                "external_url": f"https://en.wikipedia.org/wiki/{wiki_title.replace(' ', '_')}",
                "status": "article_not_found"
            }

        html = entry.get_item().content.tobytes().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')

        # Remove scripts, styles, navigation
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()

        text_content = soup.get_text(separator=' ', strip=True)

        return {
            "source_id": source_id,
            "title": wiki_title,
            "content_html": html[:50000],  # Limit to 50KB
            "content_text": text_content[:10000],  # Limit to 10KB
            "word_count": len(text_content.split()),
            "external_url": f"https://en.wikipedia.org/wiki/{wiki_title.replace(' ', '_')}",
            "status": "ok"
        }

    except ImportError:
        return {
            "source_id": source_id,
            "title": wiki_title,
            "content_html": None,
            "content_text": None,
            "external_url": f"https://en.wikipedia.org/wiki/{wiki_title.replace(' ', '_')}",
            "status": "libzim_not_installed"
        }
    except Exception as e:
        return {
            "source_id": source_id,
            "title": wiki_title,
            "content_html": None,
            "content_text": None,
            "external_url": f"https://en.wikipedia.org/wiki/{wiki_title.replace(' ', '_')}",
            "status": f"error: {str(e)}"
        }
