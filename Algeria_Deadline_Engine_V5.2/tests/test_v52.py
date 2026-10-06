from pathlib import Path
import tempfile
from engine.repository import CaseRepository
from engine.models import Case
from engine.enterprise import EnterpriseSecurity, BackupManager

def repo():
    return CaseRepository(Path(tempfile.mkdtemp())/'db.sqlite3')

def test_password_hash_and_auth():
    r=repo(); sec=EnterpriseSecurity(r); oid=sec.create_organization('Cabinet Demo'); u=sec.create_user(oid,'a@demo.test','Alice','lawyer','Secret-123!')
    assert sec.authenticate('a@demo.test','Secret-123!').id==u.id
    assert sec.authenticate('a@demo.test','bad') is None

def test_rbac_and_acl():
    r=repo(); sec=EnterpriseSecurity(r); oid=sec.create_organization('Org'); u=sec.create_user(oid,'a@x','A','assistant','pw'); c=Case.new('D-1','Test','Org'); r.create_case(c)
    assert not sec.allowed(u,'analysis:run',c.id)
    sec.grant_case(c.id,u.id,['analysis:run']); assert sec.allowed(u,'analysis:run',c.id)

def test_audit_chain():
    r=repo(); sec=EnterpriseSecurity(r); oid=sec.create_organization('Org'); u=sec.create_user(oid,'a@y','A','reviewer','pw'); sec.audit(u.id,'case.read','case:x','success',{})
    assert sec.audit_chain_valid()

def test_case_backup():
    r=repo(); sec=EnterpriseSecurity(r); c=Case.new('D-2','Backup','Org'); r.create_case(c); out=BackupManager(r).export_case(c.id,Path(tempfile.mkdtemp())/'case.zip'); assert out.exists()
