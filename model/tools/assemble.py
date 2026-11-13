import openpyxl, json, pickle, datetime as dt
D=['2026-11-12','2026-11-11','2026-11-10','2026-11-09']
ser=lambda s:(dt.date.fromisoformat(s)-dt.date(1899,12,30)).days
wb=openpyxl.load_workbook('/home/claude/stock-data-collection/Stock_data_collection.xlsx',read_only=True,data_only=True)
V={r[0].date().isoformat():r for r in wb['VTS historical data'].iter_rows(min_row=2,max_row=14,values_only=True) if r[0]}
N={r[0].date().isoformat():r for r in wb['NASDAQ historical data'].iter_rows(min_row=2,max_row=14,values_only=True) if r[0]}
cols,rows=pickle.load(open('/tmp/m2_metrice.pkl','rb'))   # A,B,C,D,E,F,G,I,J,...
M={r[0].date().isoformat():r for r in rows[:8] if r[0]}
# metrice extras: Z cash osc, AB RY, AN VIX
wbm=openpyxl.load_workbook('/mnt/user-data/uploads/Volatility_Barometer_model_2.xlsx',read_only=True,data_only=True)
from openpyxl.utils import column_index_from_string as ci
X={}
for r in wbm['Volatility Metrice'].iter_rows(min_row=5,max_row=14,values_only=True):
    if r[0]: X[r[0].date().isoformat()]=dict(cash=r[ci('Z')-1],ry=r[ci('AB')-1],vix=r[ci('AN')-1],J=r[ci('J')-1])
def G(prevJ,d):
    return 'SPY' if prevJ<0.6 else ('KO' if prevJ<0.9 else 'CAOS')   # hike cycle in Nov 2026
dates=sorted(X)   # ascending
out={}
for d in D:
    v=V[d]; n=N[d]; m=M[d]
    prev=dates[dates.index(d)-1]
    out[d]=dict(serial=ser(d),
      SPY_c=v[1],SPY_o=v[2],SSO_c=v[3],SSO_o=v[4],IYR_c=v[5],IYR_o=v[6],KO_c=v[7],KO_o=v[8],CAOS_c=v[9],CAOS_o=v[10],GLD_c=v[11],GLD_o=v[12],SVIX_c=v[13],SVIX_o=v[14],VXZ_c=v[15],VXZ_o=v[16],
      RY=v[17],VIX=v[18],R9=v[19],
      QQQ_c=n[2],QQQ_o=n[3],QLD_c=n[4],QLD_o=n[5],XLU_c=n[8],XLU_o=n[9],
      vts_tac=m[1],mod_tac=m[2],vts_def=m[3],mod_def=m[4],vts_tail=m[5],
      mod_tail=G(X[prev]['J'],d),
      prev_cash=X[prev]['cash'],prev_ry=X[prev]['ry'],prev_vix=X[prev]['vix'])
    print(d,{k:out[d][k] for k in ('vts_tac','mod_tac','vts_def','mod_def','vts_tail','mod_tail','RY','VIX','R9','prev_cash','prev_ry','prev_vix','QQQ_c','XLU_o')})
json.dump(out,open('/home/claude/newrows2.json','w'),indent=1,default=str)
