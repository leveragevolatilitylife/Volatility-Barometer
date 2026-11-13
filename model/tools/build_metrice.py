import re, json, sys, shutil, os
sys.path.insert(0,'/home/claude')
from xlshift import *
SRC='/tmp/mx/xl/worksheets/sheet5.xml'
s=open(SRC,encoding='utf8').read()
i0=s.index('<sheetData>')+len('<sheetData>'); i1=s.index('</sheetData>')
head, body, tail = s[:i0], s[i0:i1], s[i1:]
ROW=re.compile(r'<row r="(\d+)"([^>]*?)(?:/>|>(.*?)</row>)',re.S)
CELL=re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)',re.S)
FM=re.compile(r'<f([^>]*?)(?:/>|>(.*?)</f>)',re.S)
rows=[(int(m.group(1)),m.group(2),m.group(3) or '') for m in ROW.finditer(body)]
print('rows',len(rows))
# pass1 masters
masters={}
cells_by_row={}
for r,at,inner in rows:
    cl=[]
    for m in CELL.finditer(inner):
        col,rr,cat,cin=m.group(1),int(m.group(2)),m.group(3),m.group(4)
        f=None
        if cin:
            fm=FM.search(cin)
            if fm:
                fat,ftxt=fm.group(1),fm.group(2)
                assert 'array' not in fat
                si=re.search(r'si="(\d+)"',fat)
                if 't="shared"' in fat:
                    if ftxt is not None:
                        masters[si.group(1)]=(col2n(col),rr,ftxt); f=ftxt
                    else:
                        mc,mr,mt=masters[si.group(1)]
                        f=translate_rel(mt, rr-mr, col2n(col)-mc)
                else: f=ftxt
        cl.append([col,rr,cat,cin,f])
    cells_by_row[r]=(at,cl)
nform=sum(1 for r in cells_by_row for c in cells_by_row[r][1] if c[4] is not None); print('formulas',nform)
def strip_t(cat): return re.sub(r'\s+t="[^"]*"','',cat)
import pickle, datetime as _dt
VALS=pickle.load(open('/tmp/vals.pkl','rb')) if os.path.exists('/tmp/vals.pkl') else {}
from xml.sax.saxutils import escape
def fcell(col,r,cat,f):
    v=VALS.get((r,col2n(col)))
    cat=strip_t(cat)
    if v is None: return f'<c r="{col}{r}"{cat}><f>{f}</f></c>'
    if isinstance(v,bool): return f'<c r="{col}{r}"{cat} t="b"><f>{f}</f><v>{int(v)}</v></c>'
    if isinstance(v,(_dt.datetime,_dt.date)):
        v=(v-_dt.datetime(1899,12,30)).total_seconds()/86400 if isinstance(v,_dt.datetime) else (v-_dt.date(1899,12,30)).days
    if isinstance(v,str):
        t=' t="e"' if v.startswith('#') else ' t="str"'
        return f'<c r="{col}{r}"{cat}{t}><f>{f}</f><v>{escape(v)}</v></c>'
    return f'<c r="{col}{r}"{cat}><f>{f}</f><v>{repr(float(v)) if not float(v).is_integer() else int(v)}</v></c>'
out=[]
newdata=json.load(open('/home/claude/newrows.json'))
dates=['2026-11-12','2026-11-11','2026-11-10','2026-11-09']   # rows 5..8
keep_const=set()
for r in sorted(cells_by_row):
    at,cl=cells_by_row[r]
    if r==5:
        # emit new rows 5..8 first
        for k,dk in zip(range(5,9),dates):
            d=newdata[dk]; cs=[]
            for col,rr,cat,cin,f in cl:
                if f is not None:
                    ff=abs_shift_only(translate_rel(f,k-5)); cs.append(fcell(col,k,cat,ff))
                else:
                    v=None
                    if col=='A': v=d['serial']
                    elif col in d: v=d[col]
                    if v is not None: cs.append(f'<c r="{col}{k}"{strip_t(cat)}><v>{v}</v></c>')
                    else:
                        if cin and '<v>' in cin and col not in ('B','D','G','BG','BK','BL','BM','BO','BP','BQ'):
                            keep_const.add(col)
                        cs.append(f'<c r="{col}{k}"{strip_t(cat)}/>')
            out.append(f'<row r="{k}"{at}>'+''.join(cs)+'</row>')
    nr = r+N_INS if r>=R_START else r
    cs=[]
    for col,rr,cat,cin,f in cl:
        if f is not None:
            ff = shift_moving(f) if r>=R_START else shift_outside(f,'')
            cs.append(fcell(col,nr,cat,ff))
        else:
            if cin is None: cs.append(f'<c r="{col}{nr}"{cat}/>')
            else: cs.append(f'<c r="{col}{nr}"{cat}>{cin}</c>')
    out.append(f'<row r="{nr}"{at}>'+''.join(cs)+'</row>')
print('unmapped constants in template:',sorted(keep_const))
# tail edits
tail=re.sub(r'sqref="([^"]+)"',lambda m:'sqref="'+shift_sqref(m.group(1))+'"',tail)
head=head.replace('<dimension ref="A1:EN9291"/>','<dimension ref="A1:EN9295"/>')
open('/tmp/sheet5_new.xml','w',encoding='utf8').write(head+''.join(out)+tail)
print('done', len(''.join(out)))
