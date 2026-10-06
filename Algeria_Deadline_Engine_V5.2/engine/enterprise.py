from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib, hmac, json, secrets, sqlite3, zipfile
from pathlib import Path
from typing import Any

ROLES = {
    'admin': {'*'},
    'lawyer': {'case:read','case:write','document:read','document:write','analysis:run','report:export'},
    'reviewer': {'case:read','document:read','analysis:run','report:export','review:validate'},
    'assistant': {'case:read','case:write','document:read','document:write'},
    'auditor': {'case:read','document:read','audit:read','report:export'},
}

@dataclass(frozen=True)
class User:
    id: str
    organization_id: str
    email: str
    display_name: str
    role: str
    active: bool = True

class EnterpriseSecurity:
    """Small dependency-free production foundation: RBAC, password hashing, ACLs and audit."""
    def __init__(self, repo):
        self.repo = repo
        self._init()

    def _init(self):
        self.repo.conn.executescript('''
        CREATE TABLE IF NOT EXISTS organizations(
          id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users(
          id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
          display_name TEXT NOT NULL, role TEXT NOT NULL, password_hash TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS case_acl(
          case_id TEXT NOT NULL, user_id TEXT NOT NULL, permission TEXT NOT NULL,
          created_at TEXT NOT NULL, PRIMARY KEY(case_id,user_id,permission)
        );
        CREATE TABLE IF NOT EXISTS security_audit(
          id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, user_id TEXT, action TEXT NOT NULL,
          resource TEXT, outcome TEXT NOT NULL, metadata_json TEXT, previous_hash TEXT, audit_hash TEXT NOT NULL
        );
        '''); self.repo.conn.commit()

    @staticmethod
    def hash_password(password: str, salt: bytes | None = None) -> str:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)
        return f'pbkdf2_sha256$310000${salt.hex()}${digest.hex()}'

    @staticmethod
    def verify_password(password: str, encoded: str) -> bool:
        try:
            alg, rounds, salt_hex, digest_hex = encoded.split('$')
            if alg != 'pbkdf2_sha256': return False
            digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), int(rounds))
            return hmac.compare_digest(digest.hex(), digest_hex)
        except Exception: return False

    def create_organization(self, name: str) -> str:
        oid=secrets.token_hex(12); now=datetime.now(timezone.utc).isoformat()
        self.repo.conn.execute('INSERT INTO organizations VALUES (?,?,?)',(oid,name,now)); self.repo.conn.commit(); return oid

    def create_user(self, organization_id: str, email: str, display_name: str, role: str, password: str) -> User:
        if role not in ROLES: raise ValueError('Unknown role')
        uid=secrets.token_hex(12); now=datetime.now(timezone.utc).isoformat()
        self.repo.conn.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?)',(uid,organization_id,email.lower().strip(),display_name,role,self.hash_password(password),1,now)); self.repo.conn.commit()
        return User(uid,organization_id,email.lower().strip(),display_name,role,True)

    def authenticate(self, email: str, password: str) -> User | None:
        r=self.repo.conn.execute('SELECT * FROM users WHERE email=? AND active=1',(email.lower().strip(),)).fetchone()
        if not r or not self.verify_password(password,r['password_hash']):
            self.audit(None,'auth.login','user:'+email,'denied',{})
            return None
        u=User(r['id'],r['organization_id'],r['email'],r['display_name'],r['role'],bool(r['active']))
        self.audit(u.id,'auth.login','user:'+u.email,'success',{'role':u.role}); return u

    def grant_case(self, case_id: str, user_id: str, permissions: list[str]):
        now=datetime.now(timezone.utc).isoformat()
        for p in permissions:
            self.repo.conn.execute('INSERT OR IGNORE INTO case_acl VALUES (?,?,?,?)',(case_id,user_id,p,now))
        self.repo.conn.commit()

    def allowed(self, user: User, permission: str, case_id: str | None = None) -> bool:
        if not user.active or user.role not in ROLES: return False
        if '*' in ROLES[user.role] or permission in ROLES[user.role]:
            if case_id is None or user.role=='admin': return True
        if case_id:
            r=self.repo.conn.execute('SELECT 1 FROM case_acl WHERE case_id=? AND user_id=? AND permission=?',(case_id,user.id,permission)).fetchone()
            return bool(r)
        return False

    def audit(self, user_id: str | None, action: str, resource: str | None, outcome: str, metadata: dict[str,Any]):
        now=datetime.now(timezone.utc).isoformat(); prev=self.repo.conn.execute('SELECT audit_hash FROM security_audit ORDER BY timestamp DESC LIMIT 1').fetchone(); previous=prev['audit_hash'] if prev else ''
        payload={'timestamp':now,'user_id':user_id,'action':action,'resource':resource,'outcome':outcome,'metadata':metadata,'previous_hash':previous}
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        self.repo.conn.execute('INSERT INTO security_audit VALUES (?,?,?,?,?,?,?,?,?)',(secrets.token_hex(12),now,user_id,action,resource,outcome,json.dumps(metadata,ensure_ascii=False),previous,digest)); self.repo.conn.commit(); return digest

    def audit_chain_valid(self) -> bool:
        rows=self.repo.conn.execute('SELECT * FROM security_audit ORDER BY timestamp,id').fetchall(); previous=''
        for r in rows:
            payload={'timestamp':r['timestamp'],'user_id':r['user_id'],'action':r['action'],'resource':r['resource'],'outcome':r['outcome'],'metadata':json.loads(r['metadata_json'] or '{}'),'previous_hash':r['previous_hash']}
            expected=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            if r['previous_hash'] != previous or not hmac.compare_digest(expected,r['audit_hash']): return False
            previous=r['audit_hash']
        return True

    def users(self, organization_id: str):
        return [dict(r) for r in self.repo.conn.execute('SELECT id,email,display_name,role,active,created_at FROM users WHERE organization_id=? ORDER BY created_at',(organization_id,)).fetchall()]

    def security_events(self, limit=100):
        return [dict(r) for r in self.repo.conn.execute('SELECT * FROM security_audit ORDER BY timestamp DESC LIMIT ?',(limit,)).fetchall()]

class BackupManager:
    def __init__(self, repo): self.repo=repo
    def export_case(self, case_id: str, destination: str | Path) -> Path:
        case=self.repo.get_case(case_id)
        if not case: raise ValueError('Case not found')
        payload={'case':dict(case),'events':self.repo.events(case_id),'documents':self.repo.documents(case_id),'orchestration':self.repo.latest_orchestration(case_id)}
        destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('case.json',json.dumps(payload,ensure_ascii=False,default=str,indent=2))
            for d in payload['documents']:
                z.writestr(f'metadata/{d["id"]}.json',json.dumps(d,ensure_ascii=False,default=str,indent=2))
        return destination
