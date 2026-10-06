from app.i18n import tr
from engine.workspace import build_case_report

def test_translations_cover_core_labels():
    for lang in ('fr','ar','en'):
        assert tr(lang,'dashboard')
        assert tr(lang,'create')
        assert tr(lang,'disclaimer')

def test_workspace_report_builds():
    case={'id':'C1','title':'Test','reference':'DOS-1','authority':'A','jurisdiction':'Algérie','status':'open'}
    evaluation={'calculation_id':'CALC1','status':'deadline','deadline':'2026-04-01','confidence':.9,'scenarios':[]}
    report=build_case_report(case,[],[],evaluation,{},'fr')
    assert report['schema']=='legal-report.v4.4'
    assert len(report['report_hash'])==64
