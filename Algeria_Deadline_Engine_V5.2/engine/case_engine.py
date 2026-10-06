from datetime import date
from .deadline import DeadlineEngine
from .conflicts import ConflictDetector
from .scenarios import ScenarioEngine
from .evidence_graph import build_evidence_graph

class CaseEngine:
    def __init__(self, rules, deadline_engine):
        self.rules = rules
        self.deadline = deadline_engine
        self.conflicts = ConflictDetector()
        self.scenarios = ScenarioEngine(rules)

    def evaluate(self, rule_id, facts, events, today=None, documents=None, case=None):
        today = today or date.today(); rule = self.rules.get(rule_id)
        start = date.fromisoformat(facts['start_date']) if facts.get('start_date') else None
        conflicts = self.conflicts.inspect(events, rule, facts)
        if start is None:
            out={'status':'indeterminate','confidence':0.0,'confidence_label':'faible','conflicts':[c.json() for c in conflicts], 'rule':rule,
                    'scenarios':self.scenarios.generate(facts, events, rule_id)}
            out['evidence_graph']=build_evidence_graph(case or {}, events, documents or [], out, {'ruleset_id': self.rules.ruleset_id, 'ruleset_version': self.rules.version})
            return out
        duration = rule.get('duration')
        if not duration:
            out={'status':'indeterminate','confidence':0.25,'confidence_label':'faible','conflicts':[c.json() for c in conflicts], 'rule':rule,
                    'scenarios':self.scenarios.generate(facts, events, rule_id)}
            out['evidence_graph']=build_evidence_graph(case or {}, events, documents or [], out, {'ruleset_id': self.rules.ruleset_id, 'ruleset_version': self.rules.version})
            return out

        result = self.deadline.run(start, duration['value'], duration['unit'],
                                   mode=rule.get('computation_mode','calendar'),
                                   endpoint_policy=rule.get('endpoint_policy','none'),
                                   context={'rule_id':rule_id,'facts':facts,'event_count':len(events)})
        blocking=sum(1 for c in conflicts if c.severity in ('blocking','high'))
        warnings=sum(1 for c in conflicts if c.severity=='warning')
        confidence=max(0.0, min(1.0, 0.95-0.20*blocking-0.05*warnings))
        status='indeterminate' if blocking else ('expired' if today>result['deadline'] else 'in_progress')
        result.update({
            'status':status,
            'forclusion_potential': status=='expired' and not blocking,
            'confidence':round(confidence,2),
            'confidence_label':'élevée' if confidence>=.8 else 'moyenne' if confidence>=.5 else 'faible',
            'conflicts':[c.json() for c in conflicts], 'rule':rule,
            'scenarios':self.scenarios.generate(facts, events, rule_id)
        })
        result['evidence_graph']=build_evidence_graph(case or {}, events, documents or [], result, {'ruleset_id': self.rules.ruleset_id, 'ruleset_version': self.rules.version})
        return result
