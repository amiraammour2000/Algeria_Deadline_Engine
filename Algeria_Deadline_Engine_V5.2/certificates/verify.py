import json,sys
from engine.audit import verify_audit
if __name__=='__main__':
    data=json.load(open(sys.argv[1],encoding='utf-8')); print('VALID' if verify_audit(data) else 'INVALID')
