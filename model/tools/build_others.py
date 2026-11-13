import sys, json, copy
sys.path.insert(0,'/home/claude')
from shiftsheet import *
nd=json.load(open('/home/claude/newrows2.json'))
D=['2026-11-12','2026-11-11','2026-11-10','2026-11-09']   # rows 4..7
def spec(num,d):
    x=nd[d]; s=x['serial']
    base={6:dict(A=s,B=x['QQQ_c'],F=x['XLU_c'],I=x['XLU_o'],L=x['QLD_c'],O=x['QLD_o'],R=1,S=x['VIX'],T=x['RY'],Z=x['vts_def'],BF=s),
          7:dict(A=s,B=x['QQQ_c'],F=x['XLU_c'],I=x['XLU_o'],L=x['QLD_c'],O=x['QLD_o'],R=1,S=x['VIX'],T=x['RY'],Z=x['mod_def']),
          8:dict(A=s,B=x['GLD_c'],E=x['GLD_o'],H=x['SVIX_c'],K=x['SVIX_o'],N=x['VXZ_c'],Q=x['VXZ_o'],T=1,U=x['VIX'],V=x['RY'],Z=x['R9'],AB=x['vts_tac'],BG=s),
          9:dict(A=s,B=x['GLD_c'],E=x['GLD_o'],H=x['SVIX_c'],K=x['SVIX_o'],N=x['VXZ_c'],Q=x['VXZ_o'],T=1,U=x['VIX'],V=x['RY'],Z=x['R9'],AB=x['mod_tac'],BG=s),
          10:dict(A=s,B=x['IYR_c'],E=x['IYR_o'],H=x['KO_c'],K=x['KO_o'],N=x['SPY_c'],Q=x['SPY_o'],T=x['CAOS_c'],W=x['CAOS_o'],Z=1,AA=x['vts_tail'],BG=s),
          11:dict(A=s,B=x['IYR_c'],E=x['IYR_o'],H=x['KO_c'],K=x['KO_o'],N=x['SPY_c'],Q=x['SPY_o'],T=x['CAOS_c'],W=x['CAOS_o'],Z=1,AA='Hike',AB=x['mod_tail'],BH=s)}
    return base[num]
LABELS={6:{'CI':'QQQ'},7:{'CI':'QQQ'},8:{'BT':'SVIX'},9:{'BT':'SVIX'},10:{'BT':'SPY'},11:{'BU':'SPY'}}
def build(num,out):
    sh=Sheet(f'/tmp/m2/xl/worksheets/sheet{num}.xml')
    rep=sh.shift_columns()
    for i,d in enumerate(D):
        r=4+i
        for col,val in spec(num,d).items():
            if isinstance(val,str): sh.setcell(r,col,isx=f'<is><t>{val}</t></is>')
            else: sh.setcell(r,col,v=repr(val) if isinstance(val,float) else str(val))
        for col,txt in LABELS.get(num,{}).items():
            sh.setcell(r,col,isx=f'<is><t>{txt}</t></is>')
    # drop stale cached values on formulas (recomputed later)
    for r,dd in sh.cells.items():
        for c in dd.values():
            if c['f'] is not None: c['v']=None; c['t']=None
    open(out,'w',encoding='utf8').write(sh.render())
    return sh
if __name__=='__main__':
    for n in (6,7,8,9,10,11):
        build(n,f'/tmp/sheet{n}_A.xml'); print('built',n)
