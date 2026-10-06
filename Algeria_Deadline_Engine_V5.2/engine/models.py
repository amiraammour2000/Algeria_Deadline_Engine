from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

@dataclass
class Event:
    id: str
    event_date: date
    event_type: str
    title: str
    description: str = ""
    source_document: str = ""
    legal_effect: str = "none"
    effect_status: str = "pending_validation"
    rule_ids: List[str] = field(default_factory=list)

    @classmethod
    def new(cls, event_date, event_type, title, description="", source_document=""):
        return cls(str(uuid.uuid4()), event_date, event_type, title, description, source_document)

    def json(self):
        d = asdict(self); d["event_date"] = self.event_date.isoformat(); return d

@dataclass
class Case:
    id: str
    reference: str
    title: str
    authority: str = ""
    jurisdiction: str = "Algérie"
    status: str = "open"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def new(cls, reference, title, authority=""):
        return cls(str(uuid.uuid4()), reference, title, authority)

    def json(self): return asdict(self)
