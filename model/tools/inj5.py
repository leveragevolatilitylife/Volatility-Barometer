import re, pickle
V=pickle.load(open('/tmp/lovals.pkl','rb'))[5]
s=open('/tmp/sheet5_m2.xml',encoding='utf8').read()
cnt=[0,0]
def rep(m):
    col,row,at,f=m.group(1),int(m.group(2)),m.group(3),m.group(4)
    val=V.get((row,col))
    if val is None: cnt[1]+=1; return m.group(0)
    at=re.sub(r' t="\w+"','',at)
    cnt[0]+=1
    if isinstance(val,str):
        if val.startswith('#'): return f'<c r="{col}{row}"{at} t="e">{f}<v>{val}</v></c>'
        return f'<c r="{col}{row}"{at} t="str">{f}<v>{val.replace("&","&amp;").replace("<","&lt;")}</v></c>'
    if isinstance(val,bool): return f'<c r="{col}{row}"{at} t="b">{f}<v>{int(val)}</v></c>'
    return f'<c r="{col}{row}"{at}>{f}<v>{val!r}</v></c>'
pat=re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*)>(<f>[^<]*</f>)</c>')
s=pat.sub(rep,s)
open('/tmp/sheet5_m2B.xml','w',encoding='utf8').write(s); print(cnt)
