import hashlib,json
from datetime import datetime,timezone

def canonical_hash(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':'),default=str).encode()).hexdigest()

def build_audit(case,events,evaluation,ruleset):
    record={'audit_version':'4.1','timestamp_utc':datetime.now(timezone.utc).isoformat(),'case':case,'events':events,'evaluation':evaluation,'ruleset':ruleset}
    record['audit_hash']=canonical_hash(record)
    return record

def verify_audit(record):
    expected=record.get('audit_hash')
    body={k:v for k,v in record.items() if k!='audit_hash'}
    return expected==canonical_hash(body)
