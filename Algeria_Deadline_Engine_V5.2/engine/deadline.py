from datetime import date,timedelta
from dateutil.relativedelta import relativedelta
import hashlib,json,uuid
from .calendar import AlgerianCalendar

class DeadlineEngine:
    def __init__(self, calendar, ruleset_id, ruleset_version): self.calendar=calendar; self.ruleset_id=ruleset_id; self.ruleset_version=ruleset_version
    def compute(self,start,value,unit,mode='calendar',endpoint_policy='next_working_day'):
        trace=[{'step':1,'type':'start','message':f'Point de départ retenu : {start.isoformat()}'}]
        if unit=='days': theoretical=start+timedelta(days=value)
        elif unit=='months': theoretical=start+relativedelta(months=value)
        elif unit=='years': theoretical=start+relativedelta(years=value)
        else: raise ValueError('Unité inconnue')
        trace.append({'step':2,'type':'base','message':f'Date théorique : {theoretical.isoformat()}'})
        adjusted=theoretical
        if mode=='working_days':
            adjusted=start; n=0
            while n<value:
                adjusted+=timedelta(days=1)
                if not self.calendar.is_non_working(adjusted): n+=1
            trace.append({'step':3,'type':'working_days','message':f'{value} jours ouvrés comptés depuis le lendemain du départ.'})
        elif endpoint_policy=='next_working_day' and self.calendar.is_non_working(adjusted):
            old=adjusted; adjusted=self.calendar.next_working_day(adjusted)
            trace.append({'step':3,'type':'adjustment','message':f'Report de {old.isoformat()} vers {adjusted.isoformat()}.','reasons':self.calendar.explain(old)})
        else: trace.append({'step':3,'type':'endpoint','message':'Aucun report calendaire appliqué.'})
        return adjusted,trace

    def run(self,start,value,unit,mode='calendar',endpoint_policy='next_working_day', context=None):
        deadline,trace=self.compute(start,value,unit,mode,endpoint_policy)
        context=context or {}
        payload={'start':start.isoformat(),'value':value,'unit':unit,'mode':mode,'endpoint_policy':endpoint_policy,'deadline':deadline.isoformat(),'ruleset_id':self.ruleset_id,'ruleset_version':self.ruleset_version,'context':context}
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        return {'calculation_id':'CALC-'+uuid.uuid4().hex[:12].upper(),'deadline':deadline,'trace':trace,'hash':digest,'ruleset_id':self.ruleset_id,'ruleset_version':self.ruleset_version,'input':payload}
