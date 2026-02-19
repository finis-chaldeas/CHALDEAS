"""
Unified event hierarchy classifier.

Pipeline:
1. Wikidata P361 (highest trust) - FREE
2. Period + Location matching - FREE
3. LLM classification (fallback) - PAID

Saves to event_parents table with multiple parent support.
"""
import asyncio
import sys
import os
from dataclasses import dataclass
from typing import Optional
from enum import Enum

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.event import Event
from app.models.event_parent import EventParent, ParentContext

# Support both module and script execution
try:
    from .wikidata_client import WikidataClient, WikidataEvent
    from .periods import find_period_for_event, Period, get_region
    from .validation import validate_temporal, can_be_parent, TEMPORAL_TOLERANCE
    from .llm_classifier import LLMEventClassifier, ClassificationResult, Confidence
except ImportError:
    from wikidata_client import WikidataClient, WikidataEvent
    from periods import find_period_for_event, Period, get_region
    from validation import validate_temporal, can_be_parent, TEMPORAL_TOLERANCE
    from llm_classifier import LLMEventClassifier, ClassificationResult, Confidence


class ClassificationSource(Enum):
    WIKIDATA = "wikidata"
    PERIOD = "period"
    LLM = "llm"
    MANUAL = "manual"


@dataclass
class UnifiedResult:
    """Result from unified classification."""
    event_id: int
    source: ClassificationSource
    parent_event_id: Optional[int]  # DB ID
    parent_event_title: Optional[str]
    parent_event_qid: Optional[str]
    is_primary: bool
    context: str
    confidence: float
    reasoning: str
    warnings: list[str]

    # For creating new aggregate events
    needs_parent_creation: bool = False
    parent_info: Optional[dict] = None


class UnifiedClassifier:
    """
    Unified classifier using multiple sources.

    Priority:
    1. Wikidata P361 (confidence: 0.95)
    2. Period matching (confidence: 0.7)
    3. LLM (confidence: varies)
    """

    def __init__(self, db: Session, use_llm: bool = True):
        self.db = db
        self.use_llm = use_llm
        self.wikidata_client = WikidataClient()
        self.llm_classifier = LLMEventClassifier() if use_llm else None

        # Cache for parent events (QID -> DB ID)
        self._parent_cache: dict[str, int] = {}
        self._parent_cache_by_name: dict[str, int] = {}

    async def close(self):
        await self.wikidata_client.close()

    async def classify_event(self, event: Event) -> list[UnifiedResult]:
        """Classify single event, return all parent relationships."""
        results = []

        # 1. Try Wikidata P361
        if event.wikidata_id:
            wd_results = await self._classify_wikidata(event)
            results.extend(wd_results)

        # 2. Try Period matching (if no Wikidata result)
        if not results:
            period_result = self._classify_period(event)
            if period_result:
                results.append(period_result)

        # 3. LLM fallback (if still no result and LLM enabled)
        if not results and self.use_llm:
            llm_results = await self._classify_llm(event)
            results.extend(llm_results)

        # 4. Mark first result as primary
        if results:
            results[0].is_primary = True

        return results

    async def _classify_wikidata(self, event: Event) -> list[UnifiedResult]:
        """Classify using Wikidata P361."""
        results = []

        wd_event = await self.wikidata_client.get_event_hierarchy(event.wikidata_id)

        if not wd_event.parent_qid:
            return []

        # Validate temporal containment
        parent_info = await self.wikidata_client.get_parent_info(wd_event.parent_qid)

        if parent_info.start_date and parent_info.end_date:
            temporal_valid, warnings = validate_temporal(
                event.date_start,
                event.date_end,
                parent_info.start_date,
                parent_info.end_date
            )
            if not temporal_valid:
                return []  # Skip this parent - temporal violation
        else:
            warnings = []

        # Find or prepare parent in DB
        parent_id = await self._get_or_prepare_parent(
            qid=wd_event.parent_qid,
            title=wd_event.parent_label or parent_info.label,
            title_ko=parent_info.label_ko,
            date_start=parent_info.start_date,
            date_end=parent_info.end_date,
            event_type_qid=parent_info.event_type_qid
        )

        # Determine context from event type
        context = self.wikidata_client.get_aggregate_type(wd_event.event_type_qid) or "general"

        result = UnifiedResult(
            event_id=event.id,
            source=ClassificationSource.WIKIDATA,
            parent_event_id=parent_id["id"] if parent_id else None,
            parent_event_title=wd_event.parent_label,
            parent_event_qid=wd_event.parent_qid,
            is_primary=True,
            context=context,
            confidence=0.95,
            reasoning=f"Wikidata P361: {wd_event.parent_label}",
            warnings=warnings,
            needs_parent_creation=parent_id.get("needs_creation", False) if parent_id else False,
            parent_info=parent_id.get("info") if parent_id else None
        )
        results.append(result)

        return results

    def _classify_period(self, event: Event) -> Optional[UnifiedResult]:
        """Classify using period definitions."""
        location_name = event.primary_location.name if event.primary_location else None
        period = find_period_for_event(event.date_start, location_name)

        if not period:
            return None

        # Find or prepare period as parent event
        parent_id = self._get_period_as_parent(period)

        return UnifiedResult(
            event_id=event.id,
            source=ClassificationSource.PERIOD,
            parent_event_id=parent_id,
            parent_event_title=period.name,
            parent_event_qid=period.qid,
            is_primary=True,
            context=period.aggregate_type,
            confidence=0.7,
            reasoning=f"Period match: {period.name} ({period.start}-{period.end})",
            warnings=[],
            needs_parent_creation=parent_id is None,
            parent_info={
                "title": period.name,
                "title_ko": period.name_ko,
                "qid": period.qid,
                "date_start": period.start,
                "date_end": period.end,
                "aggregate_type": period.aggregate_type
            } if parent_id is None else None
        )

    async def _classify_llm(self, event: Event) -> list[UnifiedResult]:
        """Classify using LLM."""
        results = []

        location_name = event.primary_location.name if event.primary_location else None
        category_name = event.category.name if event.category else None

        llm_result = await self.llm_classifier.classify(
            event_id=event.id,
            title=event.title,
            date_start=event.date_start,
            date_end=event.date_end,
            location=location_name,
            category=category_name,
            description=event.description
        )

        if not llm_result.has_parent:
            # Confirmed no parent
            return []

        if not llm_result.parent_event:
            return []

        # Validate temporal if we can find the parent
        parent_id = await self._get_or_prepare_parent(
            qid=llm_result.parent_event_qid,
            title=llm_result.parent_event,
            title_ko=llm_result.parent_event_ko
        )

        result = UnifiedResult(
            event_id=event.id,
            source=ClassificationSource.LLM,
            parent_event_id=parent_id["id"] if parent_id else None,
            parent_event_title=llm_result.parent_event,
            parent_event_qid=llm_result.parent_event_qid,
            is_primary=True,
            context=llm_result.context,
            confidence=llm_result.confidence_score,
            reasoning=llm_result.reasoning,
            warnings=llm_result.warnings,
            needs_parent_creation=parent_id.get("needs_creation", False) if parent_id else True,
            parent_info={
                "title": llm_result.parent_event,
                "title_ko": llm_result.parent_event_ko,
                "qid": llm_result.parent_event_qid
            }
        )
        results.append(result)

        # Additional parents
        for add_parent in llm_result.additional_parents:
            add_result = UnifiedResult(
                event_id=event.id,
                source=ClassificationSource.LLM,
                parent_event_id=None,
                parent_event_title=add_parent.get("name"),
                parent_event_qid=add_parent.get("qid"),
                is_primary=False,
                context=add_parent.get("context", "general"),
                confidence=llm_result.confidence_score * 0.9,  # Slightly lower
                reasoning=f"Additional parent from LLM",
                warnings=[],
                needs_parent_creation=True,
                parent_info=add_parent
            )
            results.append(add_result)

        return results

    async def _get_or_prepare_parent(
        self,
        qid: Optional[str] = None,
        title: Optional[str] = None,
        title_ko: Optional[str] = None,
        date_start: Optional[int] = None,
        date_end: Optional[int] = None,
        event_type_qid: Optional[str] = None
    ) -> Optional[dict]:
        """Get existing parent or prepare info for creation."""

        # Check cache first
        if qid and qid in self._parent_cache:
            return {"id": self._parent_cache[qid], "needs_creation": False}

        if title and title in self._parent_cache_by_name:
            return {"id": self._parent_cache_by_name[title], "needs_creation": False}

        # Try to find by QID
        if qid:
            parent = self.db.query(Event).filter(Event.wikidata_id == qid).first()
            if parent:
                self._parent_cache[qid] = parent.id
                return {"id": parent.id, "needs_creation": False}

        # Try to find by title
        if title:
            parent = self.db.query(Event).filter(Event.title == title).first()
            if parent:
                self._parent_cache_by_name[title] = parent.id
                if qid:
                    self._parent_cache[qid] = parent.id
                return {"id": parent.id, "needs_creation": False}

        # Need to create
        return {
            "id": None,
            "needs_creation": True,
            "info": {
                "title": title,
                "title_ko": title_ko,
                "qid": qid,
                "date_start": date_start,
                "date_end": date_end,
                "aggregate_type": self.wikidata_client.get_aggregate_type(event_type_qid) if event_type_qid else None
            }
        }

    def _get_period_as_parent(self, period: Period) -> Optional[int]:
        """Get period as parent event from DB."""
        if period.qid and period.qid in self._parent_cache:
            return self._parent_cache[period.qid]

        if period.name in self._parent_cache_by_name:
            return self._parent_cache_by_name[period.name]

        # Try QID
        if period.qid:
            parent = self.db.query(Event).filter(Event.wikidata_id == period.qid).first()
            if parent:
                self._parent_cache[period.qid] = parent.id
                return parent.id

        # Try name
        parent = self.db.query(Event).filter(Event.title == period.name).first()
        if parent:
            self._parent_cache_by_name[period.name] = parent.id
            return parent.id

        return None

    def save_results(self, results: list[UnifiedResult], create_missing_parents: bool = False):
        """Save classification results to event_parents table."""
        for result in results:
            if result.parent_event_id is None:
                if create_missing_parents and result.needs_parent_creation and result.parent_info:
                    # Create parent event
                    parent_id = self._create_parent_event(result.parent_info)
                    result.parent_event_id = parent_id
                else:
                    continue  # Skip - no parent ID

            # Check if already exists
            existing = self.db.query(EventParent).filter(
                EventParent.event_id == result.event_id,
                EventParent.parent_event_id == result.parent_event_id
            ).first()

            if existing:
                # Update
                existing.is_primary = result.is_primary
                existing.context = result.context
                existing.confidence = result.confidence
                existing.source = result.source.value
            else:
                # Create
                ep = EventParent(
                    event_id=result.event_id,
                    parent_event_id=result.parent_event_id,
                    is_primary=result.is_primary,
                    context=result.context,
                    source=result.source.value,
                    confidence=result.confidence
                )
                self.db.add(ep)

            # Sync primary parent to events.parent_event_id
            if result.is_primary:
                event = self.db.query(Event).get(result.event_id)
                if event:
                    event.parent_event_id = result.parent_event_id
                    event.parent_status = "confirmed" if result.confidence >= 0.8 else "pending"

        self.db.commit()

    def _create_parent_event(self, info: dict) -> int:
        """Create new aggregate parent event."""
        title_slug = info['title'].lower().replace(' ', '-').replace("'", '')
        slug = f"aggregate-{title_slug}"

        parent = Event(
            title=info.get("title", "Unknown"),
            title_ko=info.get("title_ko"),
            slug=slug,
            wikidata_id=info.get("qid"),
            date_start=info.get("date_start") or 0,
            date_end=info.get("date_end"),
            is_aggregate=True,
            hierarchy_level=2,
            importance=4,
            aggregate_type=info.get("aggregate_type"),
            parent_status="none"  # Top-level aggregate
        )

        self.db.add(parent)
        self.db.flush()

        # Cache it
        if info.get("qid"):
            self._parent_cache[info["qid"]] = parent.id
        self._parent_cache_by_name[info["title"]] = parent.id

        return parent.id


async def run_classification(
    limit: int = 100,
    offset: int = 0,
    use_llm: bool = True,
    create_parents: bool = False,
    dry_run: bool = False
):
    """Run classification pipeline."""
    db = SessionLocal()

    try:
        classifier = UnifiedClassifier(db, use_llm=use_llm)

        # Get events with parent_status='unknown' only (not yet classified)
        events = db.query(Event).filter(
            Event.parent_status == 'unknown'
        ).order_by(Event.importance.desc()).offset(offset).limit(limit).all()

        print(f"Processing {len(events)} events...")
        print("=" * 50)

        stats = {
            "wikidata": 0,
            "period": 0,
            "llm": 0,
            "no_result": 0,
            "total_parents": 0
        }

        for i, event in enumerate(events):
            results = await classifier.classify_event(event)

            if results:
                primary = results[0]
                stats[primary.source.value] += 1
                stats["total_parents"] += len(results)

                if not dry_run:
                    classifier.save_results(results, create_missing_parents=create_parents)

                print(f"[{i+1}/{len(events)}] {event.title[:50]}")
                print(f"  → {primary.parent_event_title} ({primary.source.value}, {primary.confidence:.2f})")
                if len(results) > 1:
                    print(f"  + {len(results)-1} additional parents")
            else:
                stats["no_result"] += 1
                print(f"[{i+1}/{len(events)}] {event.title[:50]}")
                print(f"  → No parent found")

        print("\n" + "=" * 50)
        print("Summary:")
        print(f"  Wikidata: {stats['wikidata']}")
        print(f"  Period: {stats['period']}")
        print(f"  LLM: {stats['llm']}")
        print(f"  No result: {stats['no_result']}")
        print(f"  Total parent relationships: {stats['total_parents']}")

    finally:
        await classifier.close()
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run event hierarchy classification")
    parser.add_argument("--limit", type=int, default=100, help="Number of events to process")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM classification")
    parser.add_argument("--create-parents", action="store_true", help="Create missing parent events")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to DB")

    args = parser.parse_args()

    asyncio.run(run_classification(
        limit=args.limit,
        offset=args.offset,
        use_llm=not args.no_llm,
        create_parents=args.create_parents,
        dry_run=args.dry_run
    ))
