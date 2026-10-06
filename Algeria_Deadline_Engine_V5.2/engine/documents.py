from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib, uuid

@dataclass
class Document:
    id: str
    case_id: str
    filename: str
    sha256: str
    mime_type: str = ''
    description: str = ''
    created_at: str = ''

    @classmethod
    def from_bytes(cls, case_id, filename, content, mime_type='', description=''):
        return cls('DOC-'+uuid.uuid4().hex[:10].upper(), case_id, filename,
                   hashlib.sha256(content).hexdigest(), mime_type, description,
                   datetime.now(timezone.utc).isoformat())

    def json(self): return asdict(self)
