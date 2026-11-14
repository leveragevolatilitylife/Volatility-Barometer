#!/usr/bin/env python3
"""週更新 Volatility Barometer 模型 xlsx（直接改 XML 以保留圖表）。
用法: update_model.py --model M.xlsx --sdc Stock_data_collection.xlsx --latest latest.xlsx
                      --extras daily_extras.csv --log log.csv --out OUT.xlsx [--assume-last YYYY-MM-DD]
流程: 偵測新交易日 -> Metrice 插列 -> 6 張策略分頁插列 -> LibreOffice 重算(取模型持股) -> 補策略分頁持股
      -> 再重算 -> 側欄複製欄 + 快取值注入 -> 打包。"""
import argparse, os, re, sys, shutil, zipfile, subprocess, datetime as dt, glob, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xlshift as XS
from xlshift import col2n, n2col, translate_rel, shift_outside, shift_moving, abs_shift_only, shift_sqref
import openpyxl
from openpyxl.utils import get_column_letter as CL
from openpyxl.utils.datetime import to_excel
from xml.sax.saxutils import escape

SHEET_METRICE = 5
SHEETS = {6: 'VTS Def', 7: 'Model Def', 8: 'VTS Tac', 9: 'Model Tac', 10: 'VTS Tail', 11: 'Model Tail'}
TITLES = {5: 'Volatility Metrice', 6: 'VTS (Defensive Rotation)', 7: 'Model (Defensive Rotation)', 8: 'VTS (Tactical Volatility)',
          9: 'Model (Tactical Volatility)', 10: 'VTS (Strategic Tail Risk)', 11: 'Model (Strategic Tail Risk)'}
FILES = {}   # 內部編號 -> 'xl/worksheets/sheetN.xml'（依分頁名稱解析，刪除/重排分頁後仍可用）
def resolve_files(X):
    wb = open(f'{X}/xl/workbook.xml', encoding='utf8').read()
    rl = open(f'{X}/xl/_rels/workbook.xml.rels', encoding='utf8').read()
    rid2t = {}
    for m in re.finditer(r'<Relationship\b[^>]*>', rl):
        t = m.group(0); i = re.search(r'Id="([^"]+)"', t); g = re.search(r'Target="([^"]+)"', t)
        if i and g: rid2t[i.group(1)] = g.group(1)
    name2file = {}
    for m in re.finditer(r'<sheet\b[^>]*>', wb):
        t = m.group(0); nm = re.search(r'name="([^"]+)"', t); rid = re.search(r'r:id="([^"]+)"', t)
        if nm and rid:
            tg = rid2t[rid.group(1)].lstrip('/')
            name2file[nm.group(1).replace('&amp;', '&')] = tg if tg.startswith('xl/') else 'xl/' + tg
    for n, t in TITLES.items():
        if t not in name2file: raise SystemExit(f'找不到分頁「{t}」，請確認分頁名稱沒有被改')
        FILES[n] = name2file[t]
    return name2file
ser = lambda d: (d - dt.date(1899, 12, 30)).days

# ---------------------------------------------------------------- data
def load_sources(a):
    sdc = openpyxl.load_workbook(a.sdc, read_only=True, data_only=True)
    V, N = {}, {}
    for r in sdc['VTS historical data'].iter_rows(min_row=2, max_row=60, values_only=True):
        if isinstance(r[0], dt.datetime): V[r[0].date()] = r
    for r in sdc['NASDAQ historical data'].iter_rows(min_row=2, max_row=60, values_only=True):
        if isinstance(r[0], dt.datetime): N[r[0].date()] = r
    lw = openpyxl.load_workbook(a.latest, read_only=True, data_only=True).worksheets[0]
    LT = {}
    for r in lw.iter_rows(min_row=5, max_row=70, max_col=20, values_only=True):
        if isinstance(r[0], dt.datetime): LT[r[0].date()] = r
    EX = {}
    for row in csv.DictReader(open(a.extras)):
        EX[dt.date.fromisoformat(row['date'])] = row
    LG = {}
    for row in csv.DictReader(open(a.log)):
        if row['slot'] == '16:00' and row['late'] == '0': LG[dt.date.fromisoformat(row['date'])] = row
    return V, N, LT, EX, LG

def fnum(x):
    try:
        return None if x in (None, '') else float(x)
    except Exception: return None

def build_rows(dates, V, N, LT, EX, LG):
    out = {}
    for d in dates:
        v, n, L, e, g = V[d], N[d], LT[d], EX.get(d, {}), LG.get(d, {})
        x = dict(serial=ser(d), date=d,
                 SPY_c=v[1], SPY_o=v[2], SSO_c=v[3], SSO_o=v[4], IYR_c=v[5], IYR_o=v[6], KO_c=v[7], KO_o=v[8],
                 CAOS_c=v[9], CAOS_o=v[10], GLD_c=v[11], GLD_o=v[12], SVIX_c=v[13], SVIX_o=v[14], VXZ_c=v[15], VXZ_o=v[16],
                 RY=v[17], VIX=v[18], R9=v[19],
                 QQQ_c=n[2], QQQ_o=n[3], QLD_c=n[4], QLD_o=n[5], XLU_c=n[8], XLU_o=n[9])
        # Metrice 欄位（model 的欄位字母）
        m = {'AM': L[12], 'AN': L[13], 'AO': L[14], 'AP': L[15], 'AQ': L[16]}
        for i, c in enumerate(['AS', 'AT', 'AU', 'AV', 'AW', 'AX', 'AY']): m[c] = L[1 + i]
        m.update(BH=fnum(e.get('VOLI')), BI=fnum(e.get('VVIX')), BM=fnum(e.get('SDEX')), BN=fnum(e.get('TDEX')), BO=fnum(e.get('SKEW')),
                 CM=x['SVIX_c'], CO=fnum(g.get('SVXY')), CQ=x['GLD_c'], CS=x['VXZ_c'], CU=x['SSO_c'], CW=x['SPY_c'],
                 CY=x['IYR_c'], DA=x['KO_c'], DC=x['CAOS_c'], DE=fnum(e.get('SPXTR')))
        x['metrice'] = m
        x['missing'] = [k for k, val in m.items() if val is None]
        out[d] = x
    return out

# ---------------------------------------------------------------- generic xml
ROW = re.compile(r'<row r="(\d+)"([^>]*?)(?:/>|>(.*?)</row>)', re.S)
CELL = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)
FM = re.compile(r'<f([^>]*?)(?:/>|>(.*?)</f>)', re.S)
def strip_t(cat): return re.sub(r'\s+t="[^"]*"', '', cat)

def fmt_num(v):
    return repr(float(v)) if not float(v).is_integer() else str(int(v))

def metrice_insert(src, dst, rows_new, N):
    """在 Metrice 第 5 列插入 N 個新列（newest first）。"""
    XS.N_INS = N
    s = open(src, encoding='utf8').read()
    i0 = s.index('<sheetData>') + len('<sheetData>'); i1 = s.index('</sheetData>')
    head, body, tail = s[:i0], s[i0:i1], s[i1:]
    masters = {}; out = []
    for m in ROW.finditer(body):
        r, at, inner = int(m.group(1)), m.group(2), m.group(3) or ''
        cl = []
        for cm in CELL.finditer(inner):
            col, rr, cat, cin = cm.group(1), int(cm.group(2)), cm.group(3), cm.group(4)
            f = None
            if cin:
                fm = FM.search(cin)
                if fm:
                    fat, ftxt = fm.group(1), fm.group(2)
                    assert 'array' not in fat
                    if 't="shared"' in fat:
                        si = re.search(r'si="(\d+)"', fat).group(1)
                        if ftxt is not None: masters[si] = (col2n(col), rr, ftxt); f = ftxt
                        else:
                            mc, mr, mt = masters[si]; f = translate_rel(mt, rr - mr, col2n(col) - mc)
                    else: f = ftxt if ftxt is not None else ''
            cl.append((col, rr, cat, cin, f))
        if r == 5:  # 新列
            for k, x in zip(range(5, 5 + N), rows_new):
                cs = []
                for col, rr, cat, cin, f in cl:
                    if f is not None:
                        cs.append(f'<c r="{col}{k}"{strip_t(cat)}><f>{abs_shift_only(translate_rel(f, k - 5))}</f></c>')
                    else:
                        v = x['serial'] if col == 'A' else x['metrice'].get(col)
                        if v is not None: cs.append(f'<c r="{col}{k}"{strip_t(cat)}><v>{fmt_num(v)}</v></c>')
                        else: cs.append(f'<c r="{col}{k}"{strip_t(cat)}/>')
                out.append(f'<row r="{k}"{at}>' + ''.join(cs) + '</row>')
        nr = r + N if r >= XS.R_START else r
        cs = []
        for col, rr, cat, cin, f in cl:
            if f is not None:
                ff = shift_moving(f) if r >= XS.R_START else shift_outside(f, '')
                cs.append(f'<c r="{col}{nr}"{strip_t(cat)}><f>{ff}</f></c>')
            elif cin is None: cs.append(f'<c r="{col}{nr}"{cat}/>')
            else: cs.append(f'<c r="{col}{nr}"{cat}>{cin}</c>')
        out.append(f'<row r="{nr}"{at}>' + ''.join(cs) + '</row>')
    tail = re.sub(r'sqref="([^"]+)"', lambda m: 'sqref="' + shift_sqref(m.group(1)) + '"', tail)
    dm = re.search(r'<dimension ref="A1:([A-Z]+)(\d+)"/>', head)
    if dm: head = head.replace(dm.group(0), f'<dimension ref="A1:{dm.group(1)}{int(dm.group(2)) + N}"/>')
    open(dst, 'w', encoding='utf8').write(head + ''.join(out) + tail)

# strategy sheets ---------------------------------------------------
class Sheet:
    def __init__(self, path):
        s = open(path, encoding='utf8').read()
        i0 = s.index('<sheetData>') + len('<sheetData>'); i1 = s.index('</sheetData>')
        self.head, self.tail = s[:i0], s[i1:]
        body = s[i0:i1]; self.rowattr = {}; self.cells = {}; masters = {}
        for m in ROW.finditer(body):
            r = int(m.group(1)); self.rowattr[r] = m.group(2); d = {}
            for cm in CELL.finditer(m.group(3) or ''):
                col, rr, at, inner = cm.groups(); rr = int(rr)
                sm = re.search(r' s="(\d+)"', at); tm = re.search(r' t="(\w+)"', at)
                c = dict(s=sm.group(1) if sm else None, t=tm.group(1) if tm else None, f=None, v=None, isx=None)
                if inner:
                    fm = FM.search(inner)
                    if fm:
                        fat, ft = fm.group(1), fm.group(2)
                        if 't="shared"' in fat:
                            si = re.search(r'si="(\d+)"', fat).group(1)
                            if ft is not None: masters[si] = (col2n(col), rr, ft); c['f'] = ft
                            else:
                                mc, mr, mt = masters[si]; c['f'] = translate_rel(mt, rr - mr, col2n(col) - mc)
                        else:
                            assert 'array' not in fat and 'dataTable' not in fat
                            c['f'] = ft if ft is not None else ''
                    vm = re.search(r'<v>(.*?)</v>', inner, re.S)
                    if vm: c['v'] = vm.group(1)
                    im = re.search(r'<is>.*?</is>', inner, re.S)
                    if im: c['isx'] = im.group(0)
                d[col] = c
            self.cells[r] = d
    def setcell(self, r, col, **kw):
        if r not in self.cells: self.cells[r] = {}; self.rowattr.setdefault(r, '')
        old = self.cells[r].get(col)
        c = dict(s=old['s'] if old else None, t=None, f=None, v=None, isx=None); c.update(kw)
        self.cells[r][col] = c
    def classify(self, lo=4, minn=100):
        import collections
        cnt = collections.defaultdict(lambda: [0, 0])
        for r, d in self.cells.items():
            if r < lo: continue
            for col, c in d.items():
                if c['f'] is not None: cnt[col][1] += 1
                elif c['v'] is not None or c['isx']: cnt[col][0] += 1
        return {c: v for c, v in cnt.items() if v[0] + v[1] >= minn}
    def shift_columns(self, N, lo=4, minn=100):
        ts = self.classify(lo, minn)
        for col in ts:
            rows = sorted(r for r in self.cells if r >= lo and col in self.cells[r])
            fr = [r for r in rows if self.cells[r][col]['f'] is not None]
            cr = [r for r in rows if self.cells[r][col]['f'] is None and (self.cells[r][col]['v'] is not None or self.cells[r][col]['isx'])]
            moved = {r: self.cells[r][col] for r in cr}
            for r in cr:
                c = self.cells[r][col]; self.cells[r][col] = dict(s=c['s'], t=None, f=None, v=None, isx=None)
            for r in sorted(moved, reverse=True):
                src = moved[r]; dest = self.cells.setdefault(r + N, {}); self.rowattr.setdefault(r + N, '')
                old = dest.get(col)
                dest[col] = dict(s=old['s'] if old and old['s'] else src['s'], t=src['t'], f=None, v=src['v'], isx=src['isx'])
            if fr:
                L = max(fr); base = self.cells[L][col]
                for k in range(1, N + 1):
                    r = L + k; ex = self.cells.get(r, {}).get(col)
                    if ex and (ex['v'] is not None or ex['isx']): continue
                    self.setcell(r, col, s=(ex['s'] if ex and ex['s'] else base['s']), f=translate_rel(base['f'], k), t=None)
    def render(self):
        out = []
        for r in sorted(self.cells):
            d = self.cells[r]; cs = []
            for col in sorted(d, key=col2n):
                c = d[col]; at = f' s="{c["s"]}"' if c['s'] else ''
                if c['f'] is not None:
                    t = f' t="{c["t"]}"' if c['t'] in ('str', 'b', 'e') and c['v'] is not None else ''
                    v = f'<v>{c["v"]}</v>' if c['v'] is not None else ''
                    cs.append(f'<c r="{col}{r}"{at}{t}><f>{c["f"]}</f>{v}</c>')
                elif c['isx']: cs.append(f'<c r="{col}{r}"{at} t="inlineStr">{c["isx"]}</c>')
                elif c['v'] is not None:
                    t = f' t="{c["t"]}"' if c['t'] else ''
                    cs.append(f'<c r="{col}{r}"{at}{t}><v>{c["v"]}</v></c>')
                else: cs.append(f'<c r="{col}{r}"{at}/>')
            out.append(f'<row r="{r}"{self.rowattr.get(r, "")}>' + ''.join(cs) + '</row>')
        return self.head + ''.join(out) + self.tail

def spec(num, x, hold):
    s = x['serial']; h = hold
    base = {6: dict(A=s, B=x['QQQ_c'], F=x['XLU_c'], I=x['XLU_o'], L=x['QLD_c'], O=x['QLD_o'], R=1, S=x['VIX'], T=x['RY'], Z=h.get('vts_def'), BF=s),
            7: dict(A=s, B=x['QQQ_c'], F=x['XLU_c'], I=x['XLU_o'], L=x['QLD_c'], O=x['QLD_o'], R=1, S=x['VIX'], T=x['RY'], Z=h.get('mod_def')),
            8: dict(A=s, B=x['GLD_c'], E=x['GLD_o'], H=x['SVIX_c'], K=x['SVIX_o'], N=x['VXZ_c'], Q=x['VXZ_o'], T=1, U=x['VIX'], V=x['RY'], Z=x['R9'], AB=h.get('vts_tac'), BG=s),
            9: dict(A=s, B=x['GLD_c'], E=x['GLD_o'], H=x['SVIX_c'], K=x['SVIX_o'], N=x['VXZ_c'], Q=x['VXZ_o'], T=1, U=x['VIX'], V=x['RY'], Z=x['R9'], AB=h.get('mod_tac'), BG=s),
            10: dict(A=s, B=x['IYR_c'], E=x['IYR_o'], H=x['KO_c'], K=x['KO_o'], N=x['SPY_c'], Q=x['SPY_o'], T=x['CAOS_c'], W=x['CAOS_o'], Z=1, AA=h.get('vts_tail'), BG=s),
            11: dict(A=s, B=x['IYR_c'], E=x['IYR_o'], H=x['KO_c'], K=x['KO_o'], N=x['SPY_c'], Q=x['SPY_o'], T=x['CAOS_c'], W=x['CAOS_o'], Z=1, AA='Hike', AB=h.get('mod_tail'), BH=s)}
    return {k: v for k, v in base[num].items() if v is not None}
LABELS = {6: {'CI': 'QQQ'}, 7: {'CI': 'QQQ'}, 8: {'BT': 'SVIX'}, 9: {'BT': 'SVIX'}, 10: {'BT': 'SPY'}, 11: {'BU': 'SPY'}}
# 側欄複製欄: 目標欄 -> (來源欄, 相對列偏移；1 = 前一交易日)
MAP = {6: {'BG': ('G', 0), 'BH': ('M', 0), 'BI': ('AM', 0), 'BL': ('BV', 0), 'BM': ('AZ', 0), 'BO': ('S', 1), 'BP': ('T', 1), 'BR': ('BK', 1), 'DA': ('AS', 0), 'BF': ('A', 0)},
       7: {'DA': ('AS', 0)},
       8: {'BH': ('O', 0), 'BI': ('I', 0), 'BJ': ('AO', 0), 'BL': ('AB', 0), 'BM': ('BX', 0), 'BN': ('BB', 0), 'BP': ('V', 1), 'BQ': ('U', 1)},
       10: {'BH': ('U', 0), 'BI': ('O', 0), 'BJ': ('AO', 0), 'BL': ('AA', 0), 'BM': ('BX', 0), 'BN': ('BB', 0)},
       11: {'BI': ('U', 0), 'BJ': ('O', 0), 'BK': ('AP', 0), 'BM': ('AB', 0), 'BN': ('BY', 0), 'BO': ('BC', 0), 'BH': ('A', 0)}}
MAP[9] = MAP[8]

def setv(sh, r, col, val):
    if isinstance(val, str): sh.setcell(r, col, isx=f'<is><t>{escape(val)}</t></is>')
    else: sh.setcell(r, col, v=fmt_num(val))

def build_strategy(num, srcdir, dst, rows_new, N, holds, vals=None):
    sh = Sheet(f'{srcdir}/{FILES[num]}')
    sh.shift_columns(N)
    for i, x in enumerate(rows_new):
        r = 4 + i; sp = spec(num, x, holds.get(x['date'], {}))
        for col, val in sp.items(): setv(sh, r, col, val)
        for col, txt in LABELS.get(num, {}).items(): setv(sh, r, col, txt)
        if vals:   # 側欄複製欄
            for col, (src, off) in MAP.get(num, {}).items():
                if col in sp: continue
                v = vals[num].get((r + off, src))
                if v is not None: setv(sh, r, col, v)
    for r, dd in sh.cells.items():
        for col, c in dd.items():
            if c['f'] is not None:
                c['v'] = None; c['t'] = None
                if vals:
                    v = vals[num].get((r, col))
                    if v is None: continue
                    if isinstance(v, str):
                        c['t'] = 'e' if v.startswith('#') else 'str'; c['v'] = escape(v)
                    elif isinstance(v, bool): c['t'] = 'b'; c['v'] = str(int(v))
                    else: c['v'] = fmt_num(v)
    open(dst, 'w', encoding='utf8').write(sh.render())

# ---------------------------------------------------------------- package / LO
def package(workdir, out, N, sheet_files):
    W = workdir + '_pkg'
    if os.path.exists(W): shutil.rmtree(W)
    shutil.copytree(workdir, W)
    for n, p in sheet_files.items(): shutil.copy(p, f'{W}/{FILES[n]}')
    if os.path.exists(W + '/xl/calcChain.xml'):
        os.remove(W + '/xl/calcChain.xml')
        ct = open(W + '/[Content_Types].xml', encoding='utf8').read()
        open(W + '/[Content_Types].xml', 'w', encoding='utf8').write(re.sub(r'<Override PartName="/xl/calcChain.xml"[^>]*/>', '', ct))
        rl = open(W + '/xl/_rels/workbook.xml.rels', encoding='utf8').read()
        open(W + '/xl/_rels/workbook.xml.rels', 'w', encoding='utf8').write(re.sub(r'<Relationship Id="[^"]*" Type="[^"]*calcChain" Target="calcChain.xml"/>', '', rl))
    wb = open(W + '/xl/workbook.xml', encoding='utf8').read()
    wb = re.sub(r'<calcPr([^>]*?)/>', lambda m: '<calcPr' + re.sub(r'\s+fullCalcOnLoad="\d"', '', m.group(1)) + ' fullCalcOnLoad="1"/>', wb)
    open(W + '/xl/workbook.xml', 'w', encoding='utf8').write(wb)
    if os.path.exists(out): os.remove(out)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(W + '/[Content_Types].xml', '[Content_Types].xml')
        for root, _, fs in os.walk(W):
            for f in fs:
                full = os.path.join(root, f); arc = os.path.relpath(full, W)
                if arc != '[Content_Types].xml': z.write(full, arc)

def shift_charts(workdir, N):
    XS.N_INS = N
    for p in glob.glob(workdir + '/xl/charts/chart*.xml'):
        t = open(p, encoding='utf8').read()
        if "Volatility Metrice'" not in t: continue
        t2 = re.sub(r'(<c:f>)(.*?)(</c:f>)', lambda m: m.group(1) + shift_outside(m.group(2), 'Volatility Metrice') + m.group(3), t, flags=re.S)
        if t2 != t: open(p, 'w', encoding='utf8').write(t2)

def lo_recalc(xlsx, outdir):
    os.makedirs(outdir, exist_ok=True)
    subprocess.run(['soffice', '--headless', '--convert-to', 'xlsx', '--outdir', outdir, xlsx], check=True, timeout=1500)
    return os.path.join(outdir, os.path.basename(xlsx))

def read_vals(xlsx, maxrows):
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    out = {}
    for n in (SHEET_METRICE, *SHEETS):
        ws = wb[TITLES[n]]; d = {}
        for i, row in enumerate(ws.iter_rows(max_row=maxrows[n], values_only=True), 1):
            for j, v in enumerate(row, 1):
                if v is None: continue
                if isinstance(v, (dt.datetime, dt.date)): v = to_excel(v)
                d[(i, CL(j))] = v
        out[n] = d
    return out

def inject(src, dst, V):
    s = open(src, encoding='utf8').read(); cnt = [0]
    def rep(m):
        col, row, at, f = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        val = V.get((row, col))
        if val is None: return m.group(0)
        at = re.sub(r' t="\w+"', '', at); cnt[0] += 1
        if isinstance(val, str):
            if val.startswith('#'): return f'<c r="{col}{row}"{at} t="e">{f}<v>{val}</v></c>'
            return f'<c r="{col}{row}"{at} t="str">{f}<v>{escape(val)}</v></c>'
        if isinstance(val, bool): return f'<c r="{col}{row}"{at} t="b">{f}<v>{int(val)}</v></c>'
        return f'<c r="{col}{row}"{at}>{f}<v>{val!r}</v></c>'
    s = re.sub(r'<c r="([A-Z]+)(\d+)"([^>]*)>(<f>[^<]*</f>)</c>', rep, s)
    open(dst, 'w', encoding='utf8').write(s); return cnt[0]

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    for k in ('model', 'sdc', 'latest', 'extras', 'log', 'out'): ap.add_argument('--' + k, required=True)
    ap.add_argument('--assume-last'); ap.add_argument('--work', default='/tmp/um'); ap.add_argument('--max-new', type=int, default=30)
    a = ap.parse_args()
    if os.path.exists(a.work): shutil.rmtree(a.work)
    os.makedirs(a.work); X = a.work + '/x'
    zipfile.ZipFile(a.model).extractall(X); resolve_files(X)
    # 最後一個日期
    s5 = open(f'{X}/{FILES[5]}', encoding='utf8').read(5_000_000)
    m = re.search(r'<c r="A5"[^>]*><v>(\d+)</v>', s5)
    last = dt.date.fromisoformat(a.assume_last) if a.assume_last else dt.date(1899, 12, 30) + dt.timedelta(days=int(m.group(1)))
    V, Nq, LT, EX, LG = load_sources(a)
    dates = sorted(d for d in V if d > last and d in Nq and d in LT)
    if not dates: print('NO_NEW_DATA last=', last); return 3
    dates = dates[:a.max_new]; N = len(dates)
    rows = build_rows(dates, V, Nq, LT, EX, LG)
    new_desc = [rows[d] for d in sorted(dates, reverse=True)]
    print('new dates:', [d.isoformat() for d in sorted(dates)], 'last=', last)
    for x in new_desc:
        if x['missing']: print('  缺資料', x['date'], x['missing'])
    # 既有的 VTS 實際持股：新列沒有（使用者自填），先空
    shift_charts(X, N)
    s5new = f'{a.work}/sheet5_new.xml'
    metrice_insert(f'{X}/{FILES[5]}', s5new, new_desc, N)
    files = {5: s5new}
    for n in SHEETS:
        build_strategy(n, X, f'{a.work}/sheet{n}_1.xml', new_desc, N, {})
        files[n] = f'{a.work}/sheet{n}_1.xml'
    p1 = f'{a.work}/pass1.xlsx'; package(X, p1, N, files)
    lo1 = lo_recalc(p1, a.work + '/lo1')
    mx = {5: 4 + N + 6, **{n: 3 + N + 6 for n in SHEETS}}
    V1 = read_vals(lo1, mx)
    holds = {}
    for i, x in enumerate(new_desc):
        r = 5 + i; g = lambda c: V1[5].get((r, c))
        holds[x['date']] = dict(mod_tac=g('C'), mod_def=g('E'), mod_tail=g('G'),
                                vts_tac=g('B'), vts_def=g('D'), vts_tail=g('F'))
    for d, h in holds.items(): print(d, h)
    for n in SHEETS:
        build_strategy(n, X, f'{a.work}/sheet{n}_2.xml', new_desc, N, holds)
        files[n] = f'{a.work}/sheet{n}_2.xml'
    p2 = f'{a.work}/pass2.xlsx'; package(X, p2, N, files)
    lo2 = lo_recalc(p2, a.work + '/lo2')
    mx2 = {5: 20000, **{n: 400 for n in SHEETS}}
    V2 = read_vals(lo2, mx2)
    for n in SHEETS:
        build_strategy(n, X, f'{a.work}/sheet{n}_3.xml', new_desc, N, holds, vals=V2)
        files[n] = f'{a.work}/sheet{n}_3.xml'
    inject(s5new, f'{a.work}/sheet5_final.xml', V2[5]); files[5] = f'{a.work}/sheet5_final.xml'
    package(X, a.out, N, files)
    # 錯誤檢查（頂端區域）
    bad = {}
    for n, d in V2.items():
        for (r, c), v in d.items():
            if isinstance(v, str) and v.startswith('#') and r <= 4 + N + 10: bad.setdefault(n, []).append((r, c, v))
    print('error cells near top:', bad)
    print('OK', a.out)
    return 0

if __name__ == '__main__': sys.exit(main())
