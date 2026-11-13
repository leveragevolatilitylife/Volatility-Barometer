import re, os, shutil, sys, zipfile
W='/tmp/outm2'
if os.path.exists(W): shutil.rmtree(W)
shutil.copytree('/tmp/m2',W)
sub=sys.argv[2]   # suffix for sheet files e.g. A or B
shutil.copy('/tmp/sheet5_m2.xml' if sub=='A' else '/tmp/sheet5_m2B.xml',W+'/xl/worksheets/sheet5.xml')
for n in (6,7,8,9,10,11): shutil.copy(f'/tmp/sheet{n}_{sub}.xml',W+f'/xl/worksheets/sheet{n}.xml')
if os.path.exists(W+'/xl/calcChain.xml'):
    os.remove(W+'/xl/calcChain.xml')
    ct=open(W+'/[Content_Types].xml',encoding='utf8').read()
    ct=re.sub(r'<Override PartName="/xl/calcChain.xml"[^>]*/>','',ct); open(W+'/[Content_Types].xml','w',encoding='utf8').write(ct)
    rl=open(W+'/xl/_rels/workbook.xml.rels',encoding='utf8').read()
    rl=re.sub(r'<Relationship Id="[^"]*" Type="[^"]*calcChain" Target="calcChain.xml"/>','',rl); open(W+'/xl/_rels/workbook.xml.rels','w',encoding='utf8').write(rl)
wb=open(W+'/xl/workbook.xml',encoding='utf8').read()
wb=re.sub(r'<calcPr([^>]*?)/>',lambda m:'<calcPr'+re.sub(r'\s+fullCalcOnLoad="\d"','',m.group(1))+' fullCalcOnLoad="1"/>',wb)
open(W+'/xl/workbook.xml','w',encoding='utf8').write(wb)
out=sys.argv[1]
if os.path.exists(out): os.remove(out)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.write(W+'/[Content_Types].xml','[Content_Types].xml')
    for root,_,fs in os.walk(W):
        for f in fs:
            full=os.path.join(root,f); arc=os.path.relpath(full,W)
            if arc!='[Content_Types].xml': z.write(full,arc)
print(os.path.getsize(out))
