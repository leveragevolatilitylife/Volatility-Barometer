import sys, pickle, re
sys.path.insert(0,'/home/claude')
from build_others import *
V=pickle.load(open('/tmp/lovals.pkl','rb'))
# col: (source col, row offset)
MAP={6:{'BG':('G',0),'BH':('M',0),'BI':('AM',0),'BL':('BV',0),'BM':('AZ',0),'BO':('S',1),'BP':('T',1),'BR':('BK',1),'DA':('AS',0),'BF':('A',0)},
     7:{'DA':('AS',0)},
     8:{'BH':('O',0),'BI':('I',0),'BJ':('AO',0),'BL':('AB',0),'BM':('BX',0),'BN':('BB',0),'BP':('V',1),'BQ':('U',1)},
     10:{'BH':('U',0),'BI':('O',0),'BJ':('AO',0),'BL':('AA',0),'BM':('BX',0),'BN':('BB',0)},
     11:{'BI':('U',0),'BJ':('O',0),'BK':('AP',0),'BM':('AB',0),'BN':('BY',0),'BO':('BC',0),'BH':('A',0)}}
MAP[9]=MAP[8]
def setv(sh,r,col,val):
    if isinstance(val,str): sh.setcell(r,col,isx=f'<is><t>{val}</t></is>')
    else: sh.setcell(r,col,v=repr(float(val)) if isinstance(val,float) else str(val))
for n in (6,7,8,9,10,11):
    sh=build(n,f'/tmp/tmp{n}.xml')
    v=V[n]; filled=0
    for i in range(4):
        r=4+i
        for col,(src,off) in MAP.get(n,{}).items():
            if col in spec(n,D[i]) : continue
            val=v.get((r+off,src))
            if val is None: continue
            setv(sh,r,col,val); filled+=1
    # inject cached values for formulas
    inj=0
    for r,dd in sh.cells.items():
        for col,c in dd.items():
            if c['f'] is not None:
                val=v.get((r,col))
                if val is None: continue
                if isinstance(val,str):
                    c['t']='str'; c['v']=val.replace('&','&amp;').replace('<','&lt;')
                elif isinstance(val,bool): c['t']='b'; c['v']=str(int(val))
                else: c['t']=None; c['v']=repr(float(val)) if isinstance(val,float) else str(val); 
                inj+=1
    open(f'/tmp/sheet{n}_B.xml','w',encoding='utf8').write(sh.render())
    print(n,'side filled',filled,'injected',inj)
