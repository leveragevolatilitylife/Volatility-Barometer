"""離線測試：以假資料跑 compute() 與整個 auto 流程（時段補記、late 標記、log.csv 欄位）。"""
import sys, os, shutil, tempfile, csv, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import fetch_live as fl
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York"); day = dt.date(2026, 11, 9); prevday = dt.date(2026, 11, 6)
LV = {"^VIX": 25.0, "^VIX9D": 24.0, "^VIX3M": 26.0, "^VIX6M": 25.5, "^VOLI": 23.0, "^GSPC": 6700.0, **{t: 50.0 + i for i, t in enumerate(fl.TICKERS)}}
def mk(d, lv):
    t0 = int(dt.datetime.combine(d, dt.time(9, 30), ET).timestamp())
    return [(t0 + 300 * i, lv + 0.01 * i, lv + 0.01 * i + 0.005) for i in range(78)]  # 09:30–15:55
class FakeCtx(fl.Ctx):
    def get_bars(self, sym):
        pre = int(dt.datetime.combine(day, dt.time(3, 15), ET).timestamp())
        raw = [(pre, 99.0, 99.0)] + mk(prevday, LV[sym] - .5) + mk(day, LV[sym])   # 盤前髒資料 99
        inrth = lambda t: dt.time(9, 30) <= dt.datetime.fromtimestamp(t, ET).time() <= dt.time(16, 15)
        return [b for b in raw if inrth(b[0])]
    def get_daily(self, sym): return [(prevday, LV[sym] - .5)]
    def get_vc(self): return (["Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"], [23.7, 22.1, 22.05, 22.05, 21.76, 21.8, 21.72, 21.7], {})
fl.Ctx = FakeCtx
# 1) 單一時段取價規則
c = FakeCtx()
b = c.get_bars("SPY")
assert fl.slot_price(b, day, "09:30")[0] == LV["SPY"]                       # 開盤取第一根 open
p, ts = fl.slot_price(b, day, "10:30"); assert dt.datetime.fromtimestamp(ts, ET).strftime("%H:%M") == "10:25"
p, ts = fl.slot_price(b, day, "16:00"); assert dt.datetime.fromtimestamp(ts, ET).strftime("%H:%M") == "15:55"
# 2) 整個 auto 流程（暫存資料夾）
tmp = tempfile.mkdtemp(); shutil.copytree(fl.DATA, tmp + "/data"); fl.DATA = tmp + "/data"
for f in ("live.json", "intraday_today.json", "log.csv", "state.json"):
    try: os.remove(os.path.join(fl.DATA, f))
    except FileNotFoundError: pass
def run(hhmm):
    os.environ["BARO_NOW"] = f"{day}T{hhmm}:00"; sys.argv = ["x", "--mode", "auto"]; fl.main()
run("09:50")       # 09:30 時段到期 (≥09:46) → 準時
run("10:46")       # 10:00(late 補記)、10:30 (準時)
run("16:25")       # 其餘時段補記 + 16:00 收盤
rows = list(csv.DictReader(open(fl.DATA + "/log.csv")))
print([(r["slot"], r["late"], r["barometer"], r["coverage"]) for r in rows])
assert [r["slot"] for r in rows] == fl.SLOTS, "14 個時段需齊全且依序"
assert rows[0]["late"] == "0" and rows[1]["late"] == "1" and rows[2]["late"] == "0"
assert float(rows[1]["coverage"]) < 0.6 and float(rows[2]["coverage"]) > 0.95
assert all(r[t] != "" for r in rows for t in fl.TICKERS), "11 檔價格皆需有值"
assert rows[0]["SPY"] == str(round(LV["SPY"], 4))
run("16:30")       # 再跑一次不應重複
assert len(list(csv.DictReader(open(fl.DATA + "/log.csv")))) == 14
print("OK")
