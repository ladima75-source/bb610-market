from __future__ import annotations
import io, zipfile, xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def _col(n:int)->str:
    s=''
    while n:
        n,r=divmod(n-1,26)
        s=chr(65+r)+s
    return s

def _cell_text(c, shared):
    t=c.attrib.get('t')
    if t=='inlineStr':
        x=c.find('m:is/m:t',NS)
        return '' if x is None else (x.text or '')
    v=c.find('m:v',NS)
    if v is None:return ''
    x=v.text or ''
    if t=='s':
        try:return shared[int(x)]
        except:return ''
    return x

def read_xlsx(data:bytes)->list[dict]:
    z=zipfile.ZipFile(io.BytesIO(data))
    shared=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        r=ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in r.findall('m:si',NS):
            shared.append(''.join((x.text or '') for x in si.findall('.//m:t',NS)))
    sheets=[x for x in z.namelist() if x.startswith('xl/worksheets/sheet') and x.endswith('.xml')]
    if not sheets:return []
    r=ET.fromstring(z.read(sorted(sheets)[0]))
    rows=[]
    for row in r.findall('.//m:sheetData/m:row',NS):
        vals={}
        for c in row.findall('m:c',NS):
            ref=c.attrib.get('r','A1')
            col=''.join(ch for ch in ref if ch.isalpha())
            vals[col]=_cell_text(c,shared)
        rows.append(vals)
    if not rows:return []
    def num(k):
        n=0
        for ch in k:n=n*26+ord(ch)-64
        return n
    maxn=max((num(k) for k in rows[0]),default=0)
    headers=[rows[0].get(_col(i),'').strip() for i in range(1,maxn+1)]
    out=[]
    for rr in rows[1:]:
        obj={}
        for i,h in enumerate(headers,1):
            if h:obj[h]=rr.get(_col(i),'')
        if any(str(v).strip() for v in obj.values()):out.append(obj)
    return out

def write_xlsx(rows:list[dict], headers:list[str])->bytes:
    sheet_rows=[]
    allrows=[{h:h for h in headers}]+rows
    for ri,row in enumerate(allrows,1):
        cells=[]
        for ci,h in enumerate(headers,1):
            v='' if row.get(h) is None else str(row.get(h))
            ref=f'{_col(ci)}{ri}'
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>')
        sheet_rows.append(f'<row r="{ri}">{"".join(cells)}</row>')
    sheet='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + \
          '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + \
          ''.join(sheet_rows) + '</sheetData></worksheet>'
    content='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'
    rels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    workbook='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Catalog" sheetId="1" r:id="rId1"/></sheets></workbook>'
    wbrel='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    styles='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="1"><xf xfId="0"/></cellXfs></styleSheet>'
    bio=io.BytesIO()
    with zipfile.ZipFile(bio,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',content)
        z.writestr('_rels/.rels',rels)
        z.writestr('xl/workbook.xml',workbook)
        z.writestr('xl/_rels/workbook.xml.rels',wbrel)
        z.writestr('xl/worksheets/sheet1.xml',sheet)
        z.writestr('xl/styles.xml',styles)
    return bio.getvalue()
