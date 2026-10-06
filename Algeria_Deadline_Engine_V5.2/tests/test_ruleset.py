import json
from pathlib import Path

def test_ruleset_has_core_articles():
    data=json.loads(Path('legal_rules/rules.json').read_text(encoding='utf-8'))
    ids={x['id'] for x in data['rules']}
    assert {'ALG-08-09-829','ALG-08-09-830-S','ALG-08-09-832'} <= ids
