import sys, json
from pathlib import Path
from datetime import date
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.repository import CaseRepository
from engine.models import Case, Event
from engine.rules import RuleRepository
from engine.calendar import AlgerianCalendar
from engine.deadline import DeadlineEngine
from engine.case_engine import CaseEngine
from engine.documents import Document
from engine.audit import build_audit, verify_audit
from engine.legal_intelligence import LegalIntelligence
from engine.legal_comparator import LegalComparator
from engine.legal_knowledge_graph import LegalKnowledgeGraph
from engine.legal_report_pdf import legal_report_pdf
from engine.workspace import build_case_report
from engine.document_intelligence import DocumentIntelligence
from engine.legal_qualification import LegalQualificationEngine
from engine.legal_research import LegalResearchEngine
from engine.legal_versioning import LegalVersioningEngine
from engine.case_orchestrator import LegalCaseOrchestrator
from engine.enterprise import EnterpriseSecurity, BackupManager, ROLES
from app.i18n import tr

st.set_page_config(page_title='Algeria Legal Case Workspace', page_icon='⚖️', layout='wide', initial_sidebar_state='expanded')

@st.cache_resource
def services():
    rules=RuleRepository(ROOT/'legal_rules/rules.json')
    sources=json.loads((ROOT/'data/legal_sources.json').read_text(encoding='utf-8'))
    jurisprudence=json.loads((ROOT/'data/jurisprudence.json').read_text(encoding='utf-8'))
    graph_data=json.loads((ROOT/'data/legal_knowledge_graph.json').read_text(encoding='utf-8'))
    intelligence=LegalIntelligence(sources,jurisprudence)
    graph=LegalKnowledgeGraph(graph_data['nodes'],graph_data['edges'])
    repo=CaseRepository(ROOT/'storage/cases.sqlite3')
    cal=AlgerianCalendar(ROOT/'data/holidays_2026.json',weekend=(4,5))
    engine=CaseEngine(rules,DeadlineEngine(cal,rules.ruleset_id,rules.version))
    qualifier=LegalQualificationEngine(rules)
    research=LegalResearchEngine(sources,rules,jurisprudence)
    versioning=LegalVersioningEngine.from_json(ROOT/'data/legal_versions.json', rules)
    orchestrator=LegalCaseOrchestrator(rules=rules, engine=engine, qualifier=qualifier, research=research, versioning=versioning, comparator=LegalComparator(graph))
    security=EnterpriseSecurity(repo)
    backup=BackupManager(repo)
    return rules,sources,jurisprudence,intelligence,LegalComparator(graph),repo,engine,DocumentIntelligence(['fra','ara','eng']),qualifier,research,versioning,orchestrator,security,backup
rules,sources,jurisprudence,intelligence,comparator,repo,engine,doc_ai,qualifier,research,versioning,orchestrator,security,backup=services()

if 'lang' not in st.session_state: st.session_state.lang='fr'
lang=st.session_state.lang

def css():
    rtl = 'direction:rtl;text-align:right;' if lang=='ar' else ''
    st.markdown(f'''<style>
    .block-container{{max-width:1500px;padding-top:1.2rem;}}
    .hero{{padding:24px 28px;border-radius:18px;background:linear-gradient(135deg,#0b1f33,#173b57);color:white;margin-bottom:18px;{rtl}}}
    .hero h1{{margin:0;font-size:30px;letter-spacing:-.5px;}}
    .hero p{{margin:7px 0 0;opacity:.82;}}
    .metric-card{{border:1px solid #dfe5eb;border-radius:14px;padding:15px;background:white;}}
    .smallcaps{{font-size:11px;letter-spacing:1.2px;text-transform:uppercase;opacity:.62;}}
    .rtl{{direction:rtl;text-align:right;}}
    [data-testid="stSidebar"]{{border-right:1px solid #e7ebef;}}
    </style>''', unsafe_allow_html=True)
css()

with st.sidebar:
    st.markdown('### ⚖️ Legal Workspace')
    st.session_state.lang=st.selectbox(tr(lang,'language'), ['fr','ar','en'], index=['fr','ar','en'].index(lang), format_func=lambda x:{'fr':'🇫🇷 Français','ar':'🇩🇿 العربية','en':'🇬🇧 English'}[x])
    lang=st.session_state.lang
    st.divider()
    cases=repo.list_cases()
    if st.button('＋ '+tr(lang,'new_case'),use_container_width=True,type='primary'):
        st.session_state.case_id=None
    if cases:
        labels={f"{r['reference']} — {r['title']}":r['id'] for r in cases}
        current=st.session_state.get('case_id')
        options=list(labels)
        default=next((i for i,k in enumerate(options) if labels[k]==current),0)
        pick=st.selectbox(tr(lang,'select_case'),options,index=default)
        st.session_state.case_id=labels[pick]
    st.divider()
    st.caption(f'{tr(lang,"professional")} · {rules.ruleset_id} · v{rules.version}')

st.markdown(f'''<div class="hero"><div class="smallcaps">Algeria Deadline Engine · V4.6</div><h1>{tr(lang,'app_name')}</h1><p>{tr(lang,'tagline')} · {tr(lang,'workspace_sub')}</p></div>''',unsafe_allow_html=True)

if not st.session_state.get('case_id'):
    st.subheader(tr(lang,'create'))
    a,b=st.columns(2)
    ref=a.text_input(tr(lang,'reference'),'DOS-2026-001')
    title=b.text_input(tr(lang,'title'),'')
    authority=a.text_input(tr(lang,'authority'),'')
    jurisdiction=b.text_input(tr(lang,'jurisdiction'),'Algérie / Algeria')
    if st.button('✓ '+tr(lang,'create'),type='primary'):
        c=repo.create_case(Case.new(ref,title,authority)); st.session_state.case_id=c.id; st.success(tr(lang,'case_created')); st.rerun()
    st.info(tr(lang,'create_first'))
    st.stop()

case=repo.get_case(st.session_state.case_id); events=repo.events(case['id']); docs=repo.documents(case['id'])

tabs=st.tabs([tr(lang,'overview'),tr(lang,'timeline'),tr(lang,'documents'),'⚖️ Qualification','🔎 Research',tr(lang,'legal'),tr(lang,'jurisprudence'),'🧭 Versions',tr(lang,'report'),tr(lang,'audit'),'🧠 Case Intelligence','🔐 Enterprise',tr(lang,'settings')])

with tabs[0]:
    st.subheader(f"{case['reference']} — {case['title']}")
    m=st.columns(4); m[0].metric(tr(lang,'status'),tr(lang,case['status']) if case['status'] in ('open','closed') else case['status']); m[1].metric(tr(lang,'events'),len(events)); m[2].metric(tr(lang,'documents_count'),len(docs)); m[3].metric(tr(lang,'calculations'),1 if 'evaluation' in st.session_state else 0)
    st.caption(f"{tr(lang,'authority')}: {case['authority'] or '—'} · {tr(lang,'jurisdiction')}: {case['jurisdiction'] or '—'}")
    c1,c2=st.columns(2)
    with c1:
        st.markdown('#### '+tr(lang,'quick_actions'))
        if st.button('⚙️ '+tr(lang,'evaluate'),use_container_width=True): st.session_state.active_tab='legal'; st.toast(tr(lang,'evaluate'))
        if case['status']=='open':
            if st.button('🔒 '+tr(lang,'close_case'),use_container_width=True):
                repo.update_case_status(case['id'],'closed'); st.rerun()
        else:
            if st.button('↻ '+tr(lang,'reopen_case'),use_container_width=True): repo.update_case_status(case['id'],'open'); st.rerun()
    with c2:
        st.markdown('#### '+tr(lang,'traceability'))
        st.info(tr(lang,'disclaimer'))
    st.markdown('#### '+tr(lang,'timeline'))
    if events:
        for e in events[-8:]: st.write(f"**{e['event_date']}** · {e['title']} · `{e['effect_status']}`")
    else: st.info(tr(lang,'no_data'))

with tabs[1]:
    st.subheader(tr(lang,'timeline'))
    d=st.date_input(tr(lang,'date'),date.today(),key='evdate')
    typ=st.selectbox(tr(lang,'event_type'),['acte_administratif','notification','reclamation','reponse','recours','evenement_interruptif','evenement_suspensif','autre'])
    title=st.text_input(tr(lang,'event_title'),key='evtitle'); desc=st.text_area(tr(lang,'description'),key='evdesc')
    effect=st.selectbox(tr(lang,'effect'),['none','interruption','suspension','extension'],format_func=lambda x:tr(lang,x))
    if st.button('＋ '+tr(lang,'add_event'),type='primary'):
        ev=Event.new(d,typ,title or typ,desc); ev.legal_effect=effect; ev.effect_status='pending_validation' if effect!='none' else 'validated'; repo.add_event(case['id'],ev); st.success(tr(lang,'event_saved')); st.rerun()
    st.divider()
    for e in repo.events(case['id']):
        with st.container(border=True):
            a,b,c=st.columns([2,4,2]); a.write(str(e['event_date'])); b.write(f"**{e['title']}**\n\n{e['description'] or '—'}"); c.write(tr(lang,e['effect_status']) if e['effect_status'] in ('pending_validation','validated') else e['effect_status'])
            if e['effect_status']=='pending_validation' and st.button('✓ '+tr(lang,'validate'),key='val_'+e['id']): repo.validate_event(e['id']); st.rerun()

with tabs[2]:
    st.subheader(tr(lang,'documents'))
    st.caption({'fr':'Extraction multilingue PDF/DOCX/images · OCR FR/AR/EN · toutes les extractions sont des propositions à valider.', 'en':'Multilingual PDF/DOCX/image extraction · FR/AR/EN OCR · every extraction is a proposal pending validation.', 'ar':'استخراج متعدد اللغات من PDF وDOCX والصور · OCR بالعربية والفرنسية والإنجليزية · كل استخراج يبقى اقتراحاً في انتظار الاعتماد.'}[lang])
    up=st.file_uploader(tr(lang,'upload'),type=['pdf','png','jpg','jpeg','docx','txt'])
    desc=st.text_input(tr(lang,'description_doc'))
    if up and st.button('＋ '+tr(lang,'save')+' + OCR',type='primary'):
        content=up.getvalue()
        doc=Document.from_bytes(case['id'],up.name,content,up.type or '',desc)
        repo.add_document(doc)
        analysis=doc_ai.analyze(doc.id,doc.filename,content,doc.mime_type)
        repo.save_document_analysis(doc.id,analysis.text,json.dumps(analysis.json(),ensure_ascii=False),'analyzed')
        st.success(f"{tr(lang,'document_saved')} · SHA-256 {doc.sha256} · {analysis.language.upper()} · {len(analysis.proposals)} propositions")
        if analysis.warnings:
            for w in analysis.warnings: st.warning(w)
        st.rerun()
    for d in docs:
        with st.container(border=True):
            a,b,c=st.columns([4,2,2])
            a.markdown(f"**{d['filename']}**")
            a.caption(f"SHA-256: {d['sha256']}")
            b.write(f"{tr(lang,'status')}: {d.get('extraction_status','not_analyzed')}")
            c.write(f"{len(json.loads(d.get('extraction_json') or '{}').get('proposals',[]))} propositions")
            st.write(d.get('description') or '—')
            if d.get('extraction_json'):
                data=json.loads(d['extraction_json']); props=data.get('proposals',[])
                with st.expander('🔎 '+({'fr':'Extraction et validation','en':'Extraction & validation','ar':'الاستخراج والاعتماد'}[lang])):
                    st.caption(f"Language: {data.get('language','?')} · Pages: {data.get('pages',1)} · OCR: {'yes' if data.get('ocr_used') else 'no'}")
                    for i,p in enumerate(props[:100]):
                        cc1,cc2,cc3=st.columns([2,5,2])
                        cc1.write(p.get('kind'))
                        cc2.write(f"**{p.get('value')}**\n\n{p.get('context','')[:220]}")
                        cc3.write(p.get('status','candidate'))
                    if data.get('text') or d.get('extracted_text'):
                        with st.expander('📄 '+({'fr':'Texte extrait','en':'Extracted text','ar':'النص المستخرج'}[lang])):
                            st.text_area('text_'+d['id'],d.get('extracted_text') or data.get('text',''),height=260)

with tabs[3]:
    title={'fr':'Qualification juridique assistée','en':'Assisted legal qualification','ar':'التكييف القانوني المساعد'}[lang]
    st.subheader(title)
    st.caption({'fr':'Le système formule des hypothèses traçables à partir des événements et des propositions documentaires validées. Il ne rend aucune qualification définitive automatiquement.', 'en':'The system formulates traceable hypotheses from events and validated document proposals. It never produces a definitive legal qualification automatically.', 'ar':'يقترح النظام فرضيات قانونية قابلة للتتبع انطلاقاً من الأحداث والاقتراحات الوثائقية المعتمدة. ولا يصدر تكييفاً قانونياً نهائياً آلياً.'}[lang])
    q_rule=st.selectbox({'fr':'Régime juridique à examiner','en':'Legal regime to examine','ar':'النظام القانوني محل الفحص'}[lang], [None]+[r['id'] for r in rules.all()], format_func=lambda x: '—' if x is None else f"{x} — {rules.get(x)['title']}", key='qualification_rule')
    if st.button('⚖️ '+({'fr':'Construire les qualifications candidates','en':'Build qualification candidates','ar':'إنشاء مقترحات التكييف'}[lang]), type='primary'):
        q=qualifier.qualify(repo.events(case['id']), repo.documents(case['id']), q_rule)
        st.session_state.qualification=q
    q=st.session_state.get('qualification')
    if q:
        a,b,c=st.columns(3)
        a.metric({'fr':'Candidats','en':'Candidates','ar':'المقترحات'}[lang],q['candidate_count'])
        b.metric({'fr':'Validés','en':'Validated','ar':'المعتمد'}[lang],q['validated_count'])
        c.metric({'fr':'Revue humaine','en':'Human review','ar':'مراجعة بشرية'}[lang],'REQUISE' if q['human_review_required'] else 'OK')
        for item in q['candidates']:
            badge='🟢' if item['confidence']>=.8 else '🟠' if item['confidence']>=.5 else '🔴'
            with st.expander(f"{badge} {item['label']} · {item['confidence']*100:.0f}% · {item['status']}"):
                st.write({'fr':'Catégorie','en':'Category','ar':'الفئة'}[lang]+f": {item['category']}")
                if item.get('rule_id'): st.write(f"Rule: {item['rule_id']}")
                st.markdown('**Rationale / Justification**')
                for r in item.get('rationale',[]): st.write('• '+r)
                if item.get('missing'):
                    st.warning(' / '.join(item['missing']))
                if item.get('evidence_ids'):
                    st.caption('Evidence: '+', '.join(item['evidence_ids']))
        if q['global_missing']:
            st.markdown('#### '+({'fr':'Éléments encore nécessaires','en':'Still required','ar':'العناصر المطلوبة'}[lang]))
            for m in q['global_missing']: st.warning(m)
        st.info(q['disclaimer'])

with tabs[4]:
    st.subheader({'fr':'🔎 Recherche juridique & sources','en':'🔎 Legal research & sources','ar':'🔎 البحث القانوني والمصادر'}[lang])
    st.caption({'fr':'Recherche structurée dans les sources enregistrées, les règles et la jurisprudence. Une correspondance n’est jamais une conclusion juridique.','en':'Structured search across registered sources, rules and case law. A match is never a legal conclusion.','ar':'بحث منظم في المصادر والقواعد والاجتهادات المسجلة. المطابقة لا تشكل أبداً نتيجة قانونية نهائية.'}[lang])
    rq=st.text_input({'fr':'Requête','en':'Query','ar':'البحث'}[lang], 'article 829 délai recours')
    rr=st.selectbox({'fr':'Règle à contextualiser','en':'Rule context','ar':'القاعدة القانونية'}[lang],[None]+[r['id'] for r in rules.all()],format_func=lambda x:'—' if x is None else f"{x} — {rules.get(x)['title']}",key='research_rule')
    if st.button('🔎 '+{'fr':'Rechercher','en':'Search','ar':'بحث'}[lang],type='primary'):
        st.session_state.research_result=research.search(rq,rr,lang)
    ro=st.session_state.get('research_result')
    if ro:
        st.metric({'fr':'Résultats','en':'Results','ar':'النتائج'}[lang],len(ro['results']))
        for item in ro['results']:
            badge='🟢' if item['status'] in {'official','verified'} else '🟠'
            with st.expander(f"{badge} {item.get('title') or item.get('id')} · {item['score']*100:.0f}%"):
                st.write(item.get('citation') or '—')
                st.write('Status:',item['status'])
                if item.get('url'): st.markdown(item['url'])
        st.info(ro['disclaimer'])

with tabs[5]:
    st.subheader(tr(lang,'legal'))
    rid=st.selectbox(tr(lang,'rule'),[r['id'] for r in rules.all()],format_func=lambda x:f"{x} — {rules.get(x)['title']}")
    start=st.date_input(tr(lang,'start_date'),date.today())
    nm=st.selectbox('Notification',[None,True,False],format_func=lambda x:'Non établi' if x is None else ('Oui' if x else 'Non'))
    facts={'start_date':start.isoformat(),'notification_mentioned':nm}
    if st.button('⚙️ '+tr(lang,'evaluate'),type='primary'):
        ev=engine.evaluate(rid,facts,events,documents=docs,case=dict(case)); audit=build_audit(dict(case),events,ev,rules.data); st.session_state.evaluation=ev; st.session_state.audit=audit; repo.save_calculation(case['id'],ev); repo.save_audit(case['id'],audit); st.success(tr(lang,'report_ready'))
    if 'evaluation' in st.session_state:
        ev=st.session_state.evaluation
        a,b,c=st.columns(3); a.metric(tr(lang,'status'),ev.get('status','—')); b.metric(tr(lang,'deadline'),str(ev.get('deadline','—'))[:10]); c.metric(tr(lang,'confidence'),f"{ev.get('confidence',0)*100:.0f}%")
        st.markdown('#### '+tr(lang,'reasoning'))
        for x in ev.get('trace',[]): st.write(f"**{x['step']}. {x['type']}** — {x['message']}")
        st.markdown('#### '+tr(lang,'scenarios'))
        for s in ev.get('scenarios',[]):
            with st.expander(s['name']): st.write(s['description']); st.caption(' · '.join(s.get('assumptions',[])))
        st.markdown('#### '+tr(lang,'attention'))
        for x in ev.get('conflicts',[]): st.warning(f"{x['severity']} — {x['message']}")

with tabs[6]:
    st.subheader(tr(lang,'jurisprudence')); st.caption(tr(lang,'jurisprudence_note'))
    q=st.text_input(tr(lang,'search'),'délai notification recours')
    selected_rule=rules.get(rid if 'rid' in locals() else rules.all()[0]['id'])
    for item in intelligence.jurisprudence.search(q,selected_rule):
        rec=item['record']; badge=tr(lang,'verified') if rec['verified'] else tr(lang,'unverified')
        with st.expander(f"{badge} · {rec['court']} · {rec['reference'] or '—'}"):
            st.write(rec['title']); st.write(rec['solution']); st.caption(rec['source_url'])
    if 'rid' in locals():
        cmp=comparator.compare(rid)
        st.markdown('#### Comparaison juridique')
        st.write(cmp['classification']);
        if cmp['human_review_required']: st.warning(tr(lang,'human_review'))

with tabs[7]:
    st.subheader({'fr':'🧭 Versions et applicabilité normative','en':'🧭 Versions & normative applicability','ar':'🧭 الإصدارات وقابلية التطبيق'}[lang])
    st.caption({'fr':'Le système distingue publication et entrée en vigueur. Une date publiée n’est jamais traitée automatiquement comme date d’effet.','en':'The system distinguishes publication from legal effectiveness. A publication date is never automatically treated as an effective date.','ar':'يميز النظام بين تاريخ النشر وتاريخ النفاذ. ولا يعتبر تاريخ النشر تلقائياً تاريخ سريان النص.'}[lang])
    vrule=st.selectbox({'fr':'Règle / article','en':'Rule / article','ar':'القاعدة / المادة'}[lang], [r['id'] for r in rules.all()], format_func=lambda x:f"{x} — {rules.get(x)['title']}", key='version_rule')
    vdate=st.date_input({'fr':'Date du fait à qualifier','en':'Date of fact','ar':'تاريخ الواقعة'}[lang], date.today(), key='version_date')
    if st.button('🧭 '+({'fr':'Déterminer la version applicable','en':'Determine applicable version','ar':'تحديد الإصدار المطبق'}[lang]), type='primary'):
        st.session_state.version_result=versioning.applicable(vrule, vdate.isoformat())
    vr=st.session_state.get('version_result')
    if vr:
        if vr['status']=='selected':
            st.success({'fr':'Version unique sélectionnée sur la base d’une date d’effet confirmée.','en':'Single version selected from a confirmed effective date.','ar':'تم اختيار إصدار واحد بناءً على تاريخ نفاذ مؤكد.'}[lang])
            st.json(vr['selected'])
        else:
            st.warning(vr.get('reason','Revue humaine requise.'))
            if vr.get('candidates'): st.json(vr['candidates'])
        st.caption('Human review required: '+str(vr['human_review_required']))
    st.markdown('#### '+({'fr':'Chronologie des versions','en':'Version timeline','ar':'الخط الزمني للإصدارات'}[lang]))
    st.json(versioning.timeline(vrule))

with tabs[8]:
    st.subheader(tr(lang,'report'))
    if 'evaluation' not in st.session_state:
        st.info(tr(lang,'no_report'))
    else:
        report=build_case_report(case,events,docs,st.session_state.evaluation,st.session_state.get('audit'),lang)
        st.success(f"{tr(lang,'report_ready')} · SHA-256 {report['report_hash']}")
        pdf=legal_report_pdf(report)
        st.download_button('📄 '+tr(lang,'download_report'),pdf,file_name=f"{case['reference']}-legal-report.pdf",mime='application/pdf',type='primary')
        st.download_button('{ } '+tr(lang,'export_json'),json.dumps(report,ensure_ascii=False,indent=2,default=str).encode('utf-8'),file_name=f"{case['reference']}-report.json",mime='application/json')
        st.json({'schema':report['schema'],'report_hash':report['report_hash'],'validation':report['validation']})

with tabs[9]:
    st.subheader(tr(lang,'audit'))
    if 'audit' in st.session_state:
        audit=st.session_state.audit; ok=verify_audit(audit); st.metric(tr(lang,'integrity'),tr(lang,'valid') if ok else tr(lang,'invalid')); st.json(audit)
    else: st.info(tr(lang,'no_data'))

with tabs[10]:
    st.subheader({'fr':'🧠 Intelligence centrale du dossier','en':'🧠 Central case intelligence','ar':'🧠 الذكاء المركزي للملف'}[lang])
    st.caption({'fr':'Orchestre les faits, pièces, qualification, recherche, version normative, calcul et comparaison. Il s’agit d’un état de workflow auditable, jamais d’une décision juridique automatique.','en':'Orchestrates facts, documents, qualification, research, normative versioning, computation and comparison. This is an auditable workflow state, never an automatic legal decision.','ar':'ينسق الوقائع والوثائق والتكييف والبحث والإصدار المعياري والحساب والمقارنة. إنها حالة سير عمل قابلة للتدقيق وليست قراراً قانونياً آلياً.'}[lang])
    selected_or_rule=st.selectbox({'fr':'Règle principale','en':'Primary rule','ar':'القاعدة الرئيسية'}[lang], [None]+[r['id'] for r in rules.all()], format_func=lambda x:'—' if x is None else f"{x} — {rules.get(x)['title']}", key='orchestration_rule')
    orch_date=st.date_input({'fr':'Date de référence','en':'Reference date','ar':'التاريخ المرجعي'}[lang], date.today(), key='orchestration_date')
    if st.button('🧠 '+({'fr':'Analyser le dossier de bout en bout','en':'Run end-to-end case analysis','ar':'تشغيل التحليل الكامل للملف'}[lang]), type='primary', use_container_width=True):
        facts={'start_date':orch_date.isoformat(),'language':lang}
        result=orchestrator.run(case=dict(case), events=repo.events(case['id']), documents=repo.documents(case['id']), rule_id=selected_or_rule, facts=facts)
        st.session_state.orchestration=result
        repo.save_orchestration(case['id'], result)
    orch=st.session_state.get('orchestration') or repo.latest_orchestration(case['id'])
    if orch:
        status=orch['readiness']
        labels={'blocked':('🔴',{'fr':'Bloqué','en':'Blocked','ar':'محظور'}),'review':('🟠',{'fr':'Revue requise','en':'Review required','ar':'مراجعة مطلوبة'}),'ready_for_human_review':('🟢',{'fr':'Prêt pour revue humaine','en':'Ready for human review','ar':'جاهز للمراجعة البشرية'})}
        icon,lab=labels.get(status,('⚪',{'fr':status,'en':status,'ar':status}))
        a,b,c,d=st.columns(4); a.metric({'fr':'État','en':'Readiness','ar':'الحالة'}[lang],f"{icon} {lab[lang]}"); b.metric({'fr':'Qualifications','en':'Qualifications','ar':'التكييفات'}[lang],orch['qualification']['candidate_count']); c.metric({'fr':'Sources','en':'Sources','ar':'المصادر'}[lang],orch['research']['results'].__len__()); d.metric({'fr':'Hash snapshot','en':'Snapshot hash','ar':'بصمة اللقطة'}[lang],orch['snapshot_hash'][:12]+'…')
        if orch['blockers']:
            st.markdown('#### '+({'fr':'Blocages','en':'Blockers','ar':'العوائق'}[lang]))
            for x in orch['blockers']: st.error(x)
        if orch['warnings']:
            st.markdown('#### '+({'fr':'Avertissements','en':'Warnings','ar':'التحذيرات'}[lang]))
            for x in orch['warnings']: st.warning(x)
        st.markdown('#### '+({'fr':'Chaîne de raisonnement et de traçabilité','en':'Reasoning & traceability chain','ar':'سلسلة الاستدلال والتتبع'}[lang]))
        for x in orch['trace']: st.write(f"**{x['step']}. {x['type']}** — {x['message']}")
        with st.expander({'fr':'Données structurées','en':'Structured data','ar':'البيانات المنظمة'}[lang]): st.json(orch)
        st.info(orch['disclaimer'])

with tabs[11]:
    st.subheader({'fr':'🔐 Sécurité & administration','en':'🔐 Security & administration','ar':'🔐 الأمان والإدارة'}[lang])
    st.caption({'fr':'Gestion des rôles, permissions, journal de sécurité et export de sauvegarde du dossier.','en':'Role management, permissions, security audit and case backup export.','ar':'إدارة الأدوار والصلاحيات وسجل الأمان وتصدير نسخة احتياطية للملف.'}[lang])
    if 'enterprise_org' not in st.session_state:
        row=repo.conn.execute('SELECT id FROM organizations ORDER BY created_at LIMIT 1').fetchone()
        st.session_state.enterprise_org=row['id'] if row else security.create_organization('Algeria Legal Workspace Demo')
    org_id=st.session_state.enterprise_org
    users=security.users(org_id)
    a,b,c=st.columns(3)
    a.metric({'fr':'Utilisateurs','en':'Users','ar':'المستخدمون'}[lang],len(users))
    c.metric({'fr':'Intégrité du journal','en':'Audit integrity','ar':'سلامة السجل'}[lang],'OK' if security.audit_chain_valid() else 'ALERTE')
    st.markdown('#### '+({'fr':'Rôles disponibles','en':'Available roles','ar':'الأدوار المتاحة'}[lang]))
    st.dataframe([{'role':k,'permissions':', '.join(sorted(v))} for k,v in ROLES.items()],use_container_width=True,hide_index=True)
    with st.expander({'fr':'Créer un utilisateur','en':'Create user','ar':'إنشاء مستخدم'}[lang]):
        e1,e2=st.columns(2); email=e1.text_input('Email',key='ent_email'); name=e2.text_input('Nom / Name',key='ent_name'); role=st.selectbox('Role',list(ROLES),key='ent_role'); pwd=st.text_input('Password',type='password',key='ent_pwd')
        if st.button('＋ '+({'fr':'Créer','en':'Create','ar':'إنشاء'}[lang]),key='ent_create'):
            if email and name and pwd:
                try: security.create_user(org_id,email,name,role,pwd); security.audit(None,'user.create','user:'+email,'success',{'role':role}); st.success('Created'); st.rerun()
                except Exception as ex: st.error(str(ex))
    if users:
        st.markdown('#### '+({'fr':'Utilisateurs','en':'Users','ar':'المستخدمون'}[lang])); st.dataframe(users,use_container_width=True,hide_index=True)
    st.markdown('#### '+({'fr':'Sauvegarde du dossier','en':'Case backup','ar':'نسخة احتياطية'}[lang]))
    if st.button('📦 '+({'fr':'Exporter le dossier','en':'Export case','ar':'تصدير الملف'}[lang]),key='ent_backup'):
        out=backup.export_case(case['id'],ROOT/'storage'/f"{case['reference']}-backup.zip"); security.audit(None,'case.backup',case['id'],'success',{'path':str(out)}); st.download_button('⬇️ Download backup',out.read_bytes(),file_name=out.name,mime='application/zip',key='ent_download')
    st.markdown('#### '+({'fr':'Journal de sécurité','en':'Security audit','ar':'سجل الأمان'}[lang]))
    st.dataframe(security.security_events(50),use_container_width=True,hide_index=True)

with tabs[12]:
    st.subheader(tr(lang,'settings'))
    st.selectbox(tr(lang,'language'),['fr','ar','en'],index=['fr','ar','en'].index(lang),key='settings_lang')
    st.caption(tr(lang,'delete_note'))
    st.markdown('#### '+tr(lang,'official_sources'))
    for s in sources[:8]: st.markdown(f"- **{s.get('title',s.get('id'))}** — {s.get('url','')}")
