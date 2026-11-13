import openpyxl, pickle, datetime
from openpyxl.utils import get_column_letter as L
from openpyxl.utils.datetime import to_excel
wb=openpyxl.load_workbook('/tmp/lo/m2_stageA.xlsx',read_only=True,data_only=True)
print(wb.sheetnames)
out={}
for n in (5,6,7,8,9,10,11):
    ws=wb.worksheets[n-1]; d={}
    for i,row in enumerate(ws.iter_rows(max_row=4010 if n==5 else 400,values_only=True),1):
        for j,v in enumerate(row,1):
            if v is None: continue
            if isinstance(v,(datetime.datetime,datetime.date)): v=to_excel(v)
            d[(i,L(j))]=v
    out[n]=d; print(n,ws.title,len(d))
pickle.dump(out,open('/tmp/lovals.pkl','wb'))
