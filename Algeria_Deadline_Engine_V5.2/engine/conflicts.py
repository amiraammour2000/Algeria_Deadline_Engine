class Conflict:
    def __init__(self, code, severity, message, rule_ids=None):
        self.code=code; self.severity=severity; self.message=message; self.rule_ids=rule_ids or []
    def json(self): return self.__dict__

class ConflictDetector:
    def inspect(self, case_events, selected_rule, facts):
        out=[]
        if not facts.get('start_date'):
            out.append(Conflict('MISSING_START','blocking','Aucun point de départ juridiquement identifié.'))
        if selected_rule and selected_rule.get('requires_human_validation'):
            out.append(Conflict('HUMAN_VALIDATION','warning','La qualification et/ou l’effet de cette règle exigent une validation humaine.',[selected_rule['id']]))
        notif=facts.get('notification_mentioned')
        if selected_rule and selected_rule.get('id')=='ALG-08-09-831' and notif is False:
            out.append(Conflict('OPPOSABILITY','high','La condition de mention du délai dans la notification n’est pas établie.',['ALG-08-09-831']))
        for e in case_events:
            if e.get('effect_status')=='pending_validation' and e.get('legal_effect') not in ('none',''):
                out.append(Conflict('UNVALIDATED_EVENT','high',f"L'événement '{e['title']}' a un effet juridique non validé.",e.get('rule_ids',[])))
        return out
