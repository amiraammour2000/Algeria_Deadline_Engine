import json, sqlite3
from pathlib import Path
from .models import Case, Event

class CaseRepository:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS cases(
          id TEXT PRIMARY KEY, reference TEXT NOT NULL, title TEXT NOT NULL,
          authority TEXT, jurisdiction TEXT, status TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS events(
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL, event_date TEXT NOT NULL,
          event_type TEXT NOT NULL, title TEXT NOT NULL, description TEXT,
          source_document TEXT, legal_effect TEXT, effect_status TEXT, rule_ids TEXT,
          FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        CREATE TABLE IF NOT EXISTS calculations(
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL, created_at TEXT NOT NULL,
          result_json TEXT NOT NULL, FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        CREATE TABLE IF NOT EXISTS audits(
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL, created_at TEXT NOT NULL,
          audit_hash TEXT NOT NULL, record_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents(
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL, filename TEXT NOT NULL,
          sha256 TEXT NOT NULL, mime_type TEXT, description TEXT, created_at TEXT NOT NULL,
          extracted_text TEXT, extraction_json TEXT, extraction_status TEXT DEFAULT 'not_analyzed',
          FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        CREATE TABLE IF NOT EXISTS orchestration_runs(
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL, created_at TEXT NOT NULL,
          readiness TEXT NOT NULL, snapshot_hash TEXT NOT NULL, result_json TEXT NOT NULL,
          FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        ''')
        for stmt in [
          "ALTER TABLE documents ADD COLUMN extracted_text TEXT",
          "ALTER TABLE documents ADD COLUMN extraction_json TEXT",
          "ALTER TABLE documents ADD COLUMN extraction_status TEXT DEFAULT 'not_analyzed'"
        ]:
            try: self.conn.execute(stmt)
            except sqlite3.OperationalError: pass
        self.conn.commit()

    def create_case(self, case):
        self.conn.execute('INSERT INTO cases VALUES (?,?,?,?,?,?,?)',
            (case.id,case.reference,case.title,case.authority,case.jurisdiction,case.status,case.created_at)); self.conn.commit(); return case

    def list_cases(self): return self.conn.execute('SELECT * FROM cases ORDER BY created_at DESC').fetchall()
    def get_case(self, cid): return self.conn.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone()

    def update_case_status(self, cid, status):
        self.conn.execute('UPDATE cases SET status=? WHERE id=?',(status,cid)); self.conn.commit()

    def validate_event(self, event_id):
        self.conn.execute("UPDATE events SET effect_status='validated' WHERE id=?",(event_id,)); self.conn.commit()

    def add_event(self, case_id, event):
        self.conn.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)',
            (event.id,case_id,event.event_date.isoformat(),event.event_type,event.title,event.description,
             event.source_document,event.legal_effect,event.effect_status,json.dumps(event.rule_ids))); self.conn.commit()

    def events(self, case_id):
        rows=self.conn.execute('SELECT * FROM events WHERE case_id=? ORDER BY event_date,id',(case_id,)).fetchall()
        out=[]
        for r in rows:
            d=dict(r); d['event_date']=__import__('datetime').date.fromisoformat(d['event_date']); d['rule_ids']=json.loads(d['rule_ids']); out.append(d)
        return out

    def save_calculation(self, cid, result):
        self.conn.execute('INSERT INTO calculations VALUES (?,?,datetime(\'now\'),?)',(result['calculation_id'],cid,json.dumps(result,default=str,ensure_ascii=False))); self.conn.commit()

    def save_audit(self, case_id, audit):
        self.conn.execute('INSERT OR REPLACE INTO audits VALUES (?,?,?,?,?)',
            (audit['evaluation']['calculation_id'], case_id, audit['timestamp_utc'], audit['audit_hash'], json.dumps(audit, default=str, ensure_ascii=False)))
        self.conn.commit()

    def add_document(self, doc):
        self.conn.execute('INSERT INTO documents(id,case_id,filename,sha256,mime_type,description,created_at) VALUES (?,?,?,?,?,?,?)',
            (doc.id, doc.case_id, doc.filename, doc.sha256, doc.mime_type, doc.description, doc.created_at)); self.conn.commit()

    def save_document_analysis(self, doc_id, extracted_text, extraction_json, status='analyzed'):
        self.conn.execute('UPDATE documents SET extracted_text=?, extraction_json=?, extraction_status=? WHERE id=?',(extracted_text,extraction_json,status,doc_id)); self.conn.commit()

    def document(self, doc_id):
        r=self.conn.execute('SELECT * FROM documents WHERE id=?',(doc_id,)).fetchone(); return dict(r) if r else None

    def documents(self, case_id):
        return [dict(r) for r in self.conn.execute('SELECT * FROM documents WHERE case_id=? ORDER BY created_at', (case_id,)).fetchall()]

    def save_orchestration(self, case_id, result):
        import uuid
        self.conn.execute(
            'INSERT INTO orchestration_runs VALUES (?,?,?,?,?,?)',
            (str(uuid.uuid4()), case_id, result.get('generated_at'), result.get('readiness','blocked'),
             result.get('snapshot_hash',''), json.dumps(result, default=str, ensure_ascii=False))
        )
        self.conn.commit()

    def latest_orchestration(self, case_id):
        row=self.conn.execute(
            'SELECT result_json FROM orchestration_runs WHERE case_id=? ORDER BY created_at DESC LIMIT 1',
            (case_id,)
        ).fetchone()
        return json.loads(row['result_json']) if row else None
