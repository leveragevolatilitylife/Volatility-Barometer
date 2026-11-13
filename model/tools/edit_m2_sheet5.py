import re
from xml.sax.saxutils import escape
src='/tmp/m2/xl/worksheets/sheet5.xml'
s=open(src,encoding='utf8').read()
TAIL="'Model (Strategic Tail Risk)'"
def gform(r):
    return (f'IF(J{r+1}&lt;0.6,"SPY",IF(J{r+1}&lt;0.9,IF(IFERROR(INDEX({TAIL}!$AA$4:$AA$2300,MATCH(A{r},{TAIL}!$A$4:$A$2300,0))="Hike",FALSE),"KO","IYR"),"CAOS"))')
cnt=0
def fix_row(m):
    global cnt
    r=int(m.group(1)); body=m.group(0)
    if 5<=r<=4003:
        new=re.sub(r'<c r="G%d"( s="\d+")?/>'%r, lambda mm: f'<c r="G{r}"{mm.group(1) or ""} t="str"><f>{gform(r)}</f></c>', body, count=1)
        if new!=body: cnt+=1
        body=new
    return body
s=re.sub(r'<row r="(\d+)"[^>]*?>.*?</row>',fix_row,s,flags=re.S)
print('G cells set',cnt)
# analysis block
def rng(c,a,b): return f'{c}{a}:{c}{b}'
def block(a,b):
    I,J=rng('I',a,b),rng('J',a,b)
    n=f'SUMPRODUCT(ISNUMBER({I})*ISNUMBER({J}))'
    f={}
    f['n']=n
    f['corr']=f'CORREL({I},{J})'
    f['bias']=f'SUMPRODUCT(ISNUMBER({I})*({J}-{I}))/{n}'
    f['mae']=f'SUMPRODUCT(ISNUMBER({I})*ABS({J}-{I}))/{n}'
    f['rmse']=f'SQRT(SUMPRODUCT(ISNUMBER({I})*({J}-{I})^2)/{n})'
    for t,k in ((0.01,'t1'),(0.02,'t2'),(0.05,'t5')):
        f[k]=f'SUMPRODUCT(ISNUMBER({I})*(ABS({J}-{I})&lt;={t}))/{n}'
    def zone(ths): return '*'.join(f'(({J}&lt;{t})=({I}&lt;{t}))' for t in ths)
    f['zt']=f'SUMPRODUCT(ISNUMBER({I})*{zone([0.65,0.98])})/{n}'
    f['zd']=f'SUMPRODUCT(ISNUMBER({I})*{zone([0.2,0.66,0.85])})/{n}'
    f['zl']=f'SUMPRODUCT(ISNUMBER({I})*{zone([0.6,0.9])})/{n}'
    for k,(v,m) in {'ht':('B','C'),'hd':('D','E'),'hl':('F','G')}.items():
        V,M=rng(v,a,b),rng(m,a,b)
        f[k]=f'SUMPRODUCT(({V}&lt;&gt;"")*({V}={M}))/SUMPRODUCT(--({V}&lt;&gt;""))'
    return f
labels=[('title','Model vs VTS Barometer 吻合率分析',146),
 ('n','樣本數（I、J 皆有值的天數）',0),('corr','相關係數 (VTS vs Model)',1115),('bias','平均偏差 (Model − VTS)',1115),
 ('mae','平均絕對誤差 MAE',1115),('rmse','均方根誤差 RMSE',1115),
 ('t1','吻合率：誤差 ≤ 1%',243),('t2','吻合率：誤差 ≤ 2%',243),('t5','吻合率：誤差 ≤ 5%',243),
 ('zt','Tactical 區間一致率 (65%/98%)',243),('zd','Defensive 區間一致率 (20%/66%/85%)',243),('zl','Tail Risk 區間一致率 (60%/90%)',243),
 ('ht','Tactical 持倉一致率 (B vs C)',243),('hd','Defensive 持倉一致率 (D vs E)',243),('hl','Tail Risk 持倉一致率 (F vs G)',243)]
all_=block(5,5705); r60=block(5,64)
cells={}
for i,(k,lab,st) in enumerate(labels,1):
    row=i
    cells.setdefault(row,[]).append(f'<c r="EW{row}" s="{146 if k=="title" else 0}" t="inlineStr"><is><t>{escape(lab)}</t></is></c>')
    if k=='title':
        cells[row].append(f'<c r="EX{row}" s="146" t="inlineStr"><is><t>全部資料</t></is></c>')
        cells[row].append(f'<c r="EY{row}" s="146" t="inlineStr"><is><t>最近 60 列</t></is></c>')
    else:
        stl=f' s="{st}"' if st else ''
        cells[row].append(f'<c r="EX{row}"{stl}><f>{all_[k]}</f></c>')
        cells[row].append(f'<c r="EY{row}"{stl}><f>{r60[k]}</f></c>')
note=len(labels)+1
cells[note]=[f'<c r="EW{note}" t="inlineStr"><is><t>註：只計算 I 欄（VTS Barometer）有填值的列；持倉一致率只計算 VTS 欄有填值的列。</t></is></c>']
def addcells(m):
    r=int(m.group(1))
    if r in cells:
        return m.group(0)[:-6]+''.join(cells[r])+'</row>'
    return m.group(0)
s=re.sub(r'<row r="(\d+)"[^>]*?>.*?</row>',addcells,s,count=0,flags=re.S) if False else s
# only touch first 20 rows efficiently
head_end=s.index('<row r="21"')
head=s[:head_end]; rest=s[head_end:]
head=re.sub(r'<row r="(\d+)"[^>]*?>.*?</row>',addcells,head,flags=re.S)
s=head+rest
s=s.replace('<dimension ref="A1:EU9295"/>','<dimension ref="A1:EY9295"/>')
open('/tmp/sheet5_m2.xml','w',encoding='utf8').write(s)
print('ok', len(s))
