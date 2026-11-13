import re, collections, json
from xml.sax.saxutils import escape
import sys
sys.path.insert(0,'/home/claude')
from xlshift import translate_rel, col2n, n2col
NINS=4
ROWRE=re.compile(r'<row r="(\d+)"([^>]*?)(?:/>|>(.*?)</row>)',re.S)
CELLRE=re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)',re.S)
FRE=re.compile(r'<f([^>]*?)(?:/>|>(.*?)</f>)',re.S)

class Sheet:
    def __init__(self,path):
        s=open(path,encoding='utf8').read()
        i0=s.index('<sheetData>')+len('<sheetData>'); i1=s.index('</sheetData>')
        self.head,self.tail=s[:i0],s[i1:]
        body=s[i0:i1]
        self.rowattr={}; self.cells={}   # cells[r][col]=dict(s,t,f,fat,v,raw)
        masters={}
        for m in ROWRE.finditer(body):
            r=int(m.group(1)); self.rowattr[r]=m.group(2); d={}
            for cm in CELLRE.finditer(m.group(3) or ''):
                col,rr,at,inner=cm.groups(); rr=int(rr)
                sm=re.search(r' s="(\d+)"',at); tm=re.search(r' t="(\w+)"',at)
                c=dict(s=sm.group(1) if sm else None,t=tm.group(1) if tm else None,f=None,v=None,isx=None)
                if inner:
                    fm=FRE.search(inner)
                    if fm:
                        fat,ft=fm.group(1),fm.group(2)
                        if 't="shared"' in fat:
                            si=re.search(r'si="(\d+)"',fat).group(1)
                            if ft is not None: masters[si]=(col2n(col),rr,ft); c['f']=ft
                            else:
                                mc,mr,mt=masters[si]; c['f']=translate_rel(mt,rr-mr,col2n(col)-mc)
                        else:
                            assert 'array' not in fat and 'dataTable' not in fat
                            c['f']=ft if ft is not None else ''
                    vm=re.search(r'<v>(.*?)</v>',inner,re.S)
                    if vm: c['v']=vm.group(1)
                    im=re.search(r'<is>.*?</is>',inner,re.S)
                    if im: c['isx']=im.group(0)
                d[col]=c
            self.cells[r]=d
    def get(self,r,col): return self.cells.get(r,{}).get(col)
    def setcell(self,r,col,**kw):
        if r not in self.cells:
            self.cells[r]={}; self.rowattr.setdefault(r,'')
        old=self.cells[r].get(col)
        c=dict(s=old['s'] if old else None,t=None,f=None,v=None,isx=None); c.update(kw)
        self.cells[r][col]=c
    def classify(self,lo=4,minn=100):
        cnt=collections.defaultdict(lambda:[0,0])
        for r,d in self.cells.items():
            if r<lo: continue
            for col,c in d.items():
                if c['f'] is not None: cnt[col][1]+=1
                elif c['v'] is not None or c['isx']: cnt[col][0]+=1
        return {c:v for c,v in cnt.items() if v[0]+v[1]>=minn}
    def shift_columns(self,lo=4,minn=100):
        ts=self.classify(lo,minn); report={}
        for col in ts:
            rows=sorted(r for r in self.cells if r>=lo and col in self.cells[r])
            fr=[r for r in rows if self.cells[r][col]['f'] is not None]
            cr=[r for r in rows if self.cells[r][col]['f'] is None and (self.cells[r][col]['v'] is not None or self.cells[r][col]['isx'])]
            # shift constants downward (process from bottom)
            moved={}
            for r in cr: moved[r]=self.cells[r][col]
            for r in cr: 
                c=self.cells[r][col]
                # leave style cell behind with empty content (keep style)
                self.cells[r][col]=dict(s=c['s'],t=None,f=None,v=None,isx=None)
            for r in sorted(moved,reverse=True):
                src=moved[r]; dest=self.cells.setdefault(r+NINS,{}); self.rowattr.setdefault(r+NINS,'')
                old=dest.get(col)
                dest[col]=dict(s=old['s'] if old and old['s'] else src['s'],t=src['t'],f=None,v=src['v'],isx=src['isx'])
            # extend formulas downward
            if fr:
                L=max(fr); base=self.cells[L][col]
                for k in range(1,NINS+1):
                    r=L+k
                    # do not overwrite a moved constant (formula columns with trailing const)
                    ex=self.cells.get(r,{}).get(col)
                    if ex and (ex['v'] is not None or ex['isx']): continue
                    self.setcell(r,col,s=(ex['s'] if ex and ex['s'] else base['s']),f=translate_rel(base['f'],k),t=None)
            report[col]=(len(cr),len(fr))
        return report
    def render(self):
        out=[]
        for r in sorted(self.cells):
            d=self.cells[r]; cs=[]
            for col in sorted(d,key=col2n):
                c=d[col]; at=f' s="{c["s"]}"' if c['s'] else ''
                if c['f'] is not None:
                    t=f' t="{c["t"]}"' if c['t'] in ('str','b','e') and c['v'] is not None else ''
                    v=f'<v>{c["v"]}</v>' if c['v'] is not None else ''
                    cs.append(f'<c r="{col}{r}"{at}{t}><f>{c["f"]}</f>{v}</c>')
                elif c['isx']:
                    cs.append(f'<c r="{col}{r}"{at} t="inlineStr">{c["isx"]}</c>')
                elif c['v'] is not None:
                    t=f' t="{c["t"]}"' if c['t'] else ''
                    cs.append(f'<c r="{col}{r}"{at}{t}><v>{c["v"]}</v></c>')
                else:
                    cs.append(f'<c r="{col}{r}"{at}/>')
            out.append(f'<row r="{r}"{self.rowattr.get(r,"")}>'+''.join(cs)+'</row>')
        return self.head+''.join(out)+self.tail
