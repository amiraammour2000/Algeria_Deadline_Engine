from io import BytesIO
from datetime import datetime,timezone
import hashlib,json,qrcode
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def certificate_pdf(audit):
    cert_payload={'audit_hash':audit['audit_hash'],'case_id':audit['case']['id'],'calculation_id':audit['evaluation'].get('calculation_id'),'ruleset':audit['ruleset'].get('ruleset_id'),'ruleset_version':audit['ruleset'].get('ruleset_version')}
    cert_hash=hashlib.sha256(json.dumps(cert_payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    qr=qrcode.make('ALG-V4.1|AUDIT:'+audit['audit_hash']+'|CERT:'+cert_hash); qbuf=BytesIO(); qr.save(qbuf,format='PNG'); qbuf.seek(0)
    out=BytesIO(); doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42); s=getSampleStyleSheet()
    ev=audit['evaluation']; rows=[['Dossier',audit['case']['reference']],['Objet',audit['case']['title']],['Statut',ev.get('status','')],['Confiance',str(ev.get('confidence',''))],['Échéance',str(ev.get('deadline',''))],['Règle',ev.get('rule',{}).get('id','')],['Ruleset',audit['ruleset'].get('ruleset_id','')],['Version',audit['ruleset'].get('ruleset_version','')],['Audit SHA-256',audit['audit_hash']],['Certificat SHA-256',cert_hash]]
    story=[Paragraph('ALGERIA DEADLINE ENGINE V4.1',s['Title']),Paragraph('CERTIFICAT DE TRACE ET DE COMPUTATION',s['Heading2']),Spacer(1,12)]
    t=Table(rows,colWidths=[140,345]); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.grey),('BACKGROUND',(0,0),(0,-1),colors.whitesmoke),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'TOP')])); story += [t,Spacer(1,16),Image(qbuf,width=90,height=90),Spacer(1,8),Paragraph('Certificat technique. Il atteste la trace et l’intégrité du calcul présenté ; il ne constitue pas à lui seul une opinion juridique.',s['BodyText'])]; doc.build(story); return out.getvalue(),cert_hash
