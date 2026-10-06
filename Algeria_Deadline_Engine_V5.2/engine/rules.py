import json
from pathlib import Path

class RuleRepository:
    def __init__(self, path): self.data=json.loads(Path(path).read_text(encoding='utf-8'))
    @property
    def ruleset_id(self): return self.data['ruleset_id']
    @property
    def version(self): return self.data['ruleset_version']
    def all(self): return self.data['rules']
    def get(self, rid):
        for r in self.all():
            if r['id']==rid: return r
        raise KeyError(rid)

    def source_map(self): return {x['id']:x for x in self.data.get('normative_sources',[])}
