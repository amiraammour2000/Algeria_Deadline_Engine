from datetime import date, timedelta
import json
from pathlib import Path
class AlgerianCalendar:
    def __init__(self, holiday_file=None, weekend=(4,5)):
        self.weekend=set(weekend); self.holidays=set()
        if holiday_file and Path(holiday_file).exists():
            data=json.loads(Path(holiday_file).read_text(encoding='utf-8'))
            self.holidays={date.fromisoformat(x) for x in data.get('holidays',[])}
    def is_non_working(self,d): return d.weekday() in self.weekend or d in self.holidays
    def next_working_day(self,d):
        while self.is_non_working(d): d+=timedelta(days=1)
        return d
    def explain(self,d):
        r=[]
        if d.weekday() in self.weekend: r.append('repos hebdomadaire configuré')
        if d in self.holidays: r.append('jour férié enregistré')
        return r
