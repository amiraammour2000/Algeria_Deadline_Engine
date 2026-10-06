from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib, re

DATE_PATTERNS = [
    re.compile(r'\b(\d{1,2})[\s./-](\d{1,2})[\s./-](\d{4})\b'),
    re.compile(r'\b(\d{4})[\s./-](\d{1,2})[\s./-](\d{1,2})\b'),
]
LEGAL_REF_PATTERNS = [
    re.compile(r'\b(?:loi|loi n[°ºo]?|law|قانون)\s*(?:n[°ºo]?\s*)?[0-9]{1,2}[-/]?[0-9]{1,2}\b', re.I),
    re.compile(r'\b(?:décret|decree|مرسوم)\s*(?:n[°ºo]?\s*)?[0-9]{1,4}[-/]?[0-9]{1,4}\b', re.I),
    re.compile(r'\b(?:article|art\.?|المادة)\s*[0-9]{1,4}\b', re.I),
]
COURT_TERMS = [
    'Cour suprême','Conseil d’Etat','tribunal administratif','cour administrative','محكمة عليا','مجلس الدولة','المحكمة العليا','المجلس القضائي','Supreme Court','Council of State'
]

@dataclass
class ExtractionProposal:
    kind: str
    value: str
    confidence: float
    page: Optional[int] = None
    context: str = ''
    status: str = 'candidate'

    def json(self): return asdict(self)

@dataclass
class DocumentAnalysis:
    document_id: str
    filename: str
    sha256: str
    mime_type: str
    language: str
    pages: int
    text: str
    proposals: List[ExtractionProposal]
    ocr_used: bool = False
    ocr_languages: List[str] = None
    warnings: List[str] = None

    def json(self):
        d=asdict(self); d['proposals']=[p.json() for p in self.proposals]
        return d

class DocumentIntelligence:
    """Extract text and candidate legal facts. Nothing is automatically validated."""
    def __init__(self, ocr_languages: Optional[List[str]]=None):
        self.ocr_languages = ocr_languages or ['fra','ara','eng']

    def analyze(self, document_id: str, filename: str, content: bytes, mime_type: str='') -> DocumentAnalysis:
        sha=hashlib.sha256(content).hexdigest()
        suffix=Path(filename).suffix.lower()
        text=''; pages=1; ocr_used=False; warnings=[]
        if suffix == '.pdf' or mime_type == 'application/pdf':
            text,pages,ocr_used,warnings=self._pdf(content)
        elif suffix == '.docx' or 'word' in mime_type:
            text,pages,warnings=self._docx(content)
        elif suffix in {'.txt','.md','.csv'} or mime_type.startswith('text/'):
            text=content.decode('utf-8','replace'); pages=max(1,text.count('\f')+1)
        elif suffix in {'.png','.jpg','.jpeg','.tif','.tiff','.webp'} or mime_type.startswith('image/'):
            text,ocr_used,warnings=self._image(content)
        else:
            warnings.append('Format non pris en charge pour extraction automatique.')
        language=self.detect_language(text)
        proposals=self.propose(text)
        return DocumentAnalysis(document_id,filename,sha,mime_type,language,pages,text,proposals,ocr_used,self.ocr_languages,warnings)

    def _pdf(self, content):
        try:
            import fitz
            doc=fitz.open(stream=content,filetype='pdf'); chunks=[]; ocr=False; warnings=[]
            for i,page in enumerate(doc):
                txt=page.get_text('text') or ''
                if txt.strip(): chunks.append(f'\n[PAGE {i+1}]\n{txt}')
                else: chunks.append(f'\n[PAGE {i+1}]\n'); ocr=True
            text=''.join(chunks); pages=len(doc)
            if ocr:
                try:
                    import pytesseract
                    from PIL import Image
                    import io
                    parts=[]
                    for i,page in enumerate(doc):
                        pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5), alpha=False)
                        img=Image.open(io.BytesIO(pix.tobytes('png')))
                        try: t=pytesseract.image_to_string(img, lang='+'.join(self.ocr_languages))
                        except Exception:
                            t=pytesseract.image_to_string(img)
                        parts.append(f'\n[PAGE {i+1}]\n{t}')
                    text=''.join(parts)
                except Exception as e:
                    warnings.append(f'OCR indisponible ou langues absentes: {type(e).__name__}')
            return text,pages,ocr,warnings
        except Exception as e:
            return '',1,False,[f'PDF illisible: {e}']

    def _docx(self, content):
        try:
            from docx import Document
            import io
            d=Document(io.BytesIO(content)); text='\n'.join(p.text for p in d.paragraphs)
            return text,1,[]
        except Exception as e: return '',1,[f'DOCX illisible: {e}']

    def _image(self, content):
        try:
            import pytesseract, io
            from PIL import Image
            img=Image.open(io.BytesIO(content))
            try: text=pytesseract.image_to_string(img,lang='+'.join(self.ocr_languages))
            except Exception: text=pytesseract.image_to_string(img)
            return text,True,[]
        except Exception as e: return '',False,[f'OCR image indisponible: {e}']

    @staticmethod
    def detect_language(text: str) -> str:
        if not text.strip(): return 'unknown'
        arabic=sum(1 for c in text if '\u0600' <= c <= '\u06ff')
        latin=sum(1 for c in text if ('a'<=c.lower()<='z'))
        if arabic > max(10, latin*0.2): return 'ar'
        lower=text.lower()
        fr=sum(lower.count(x) for x in [' le ',' la ',' les ',' des ',' du ',' une ',' et '])
        en=sum(lower.count(x) for x in [' the ',' and ',' of ',' to ',' with '])
        return 'fr' if fr>=en else 'en'

    @staticmethod
    def propose(text: str) -> List[ExtractionProposal]:
        out=[]
        lines=text.splitlines()
        for i,line in enumerate(lines):
            for p in DATE_PATTERNS:
                for m in p.finditer(line):
                    value=m.group(0)
                    if p.pattern.startswith(r'\b(\d{4})'):
                        norm=f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
                    else:
                        norm=f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}'
                    out.append(ExtractionProposal('date',norm,0.92,None,line.strip()))
            for p in LEGAL_REF_PATTERNS:
                for m in p.finditer(line): out.append(ExtractionProposal('legal_reference',m.group(0),0.80,None,line.strip()))
            for term in COURT_TERMS:
                if term.lower() in line.lower(): out.append(ExtractionProposal('jurisdiction',term,0.78,None,line.strip()))
        # de-duplicate while preserving order
        seen=set(); clean=[]
        for p in out:
            k=(p.kind,p.value,p.context)
            if k not in seen: seen.add(k); clean.append(p)
        return clean[:250]
