"""離線測試：以假資料跑完整 compute()，確認管線不出錯。"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import fetch_live as fl
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")
day = dt.date(2026, 11, 9)
base = int(dt.datetime.combine(day, dt.time(9, 30), ET).timestamp())
def fake_yahoo(sym, interval, rng):
    lv = {"^VIX": 25.0, "^VIX9D": 24.0, "^VIX3M": 26.0, "^VIX6M": 25.5, "^VOLI": 23.0, "^GSPC": 6700.0}[sym]
    if interval == "5m": return [(base + 300 * i, lv + 0.01 * i) for i in range(13)], {}
    return [(int(dt.datetime.combine(day - dt.timedelta(days=k), dt.time(16), ET).timestamp()), lv) for k in (5, 4, 3, 2, 1)], {}
fl.yahoo = fake_yahoo
fl.volchart = lambda: (["Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"], [23.7, 22.1, 22.05, 22.05, 21.76, 21.8, 21.72, 21.7], {})
r = fl.compute(dt.datetime.combine(day, dt.time(10, 45), ET), dt.time(10, 30))
print(r["barometer"], r["coverage"], r["strategies"], r["bar_time_et"], r["inputs"]["futures"])
assert 0 <= r["barometer"] <= 1 and r["coverage"] > 0.9 and r["bar_time_et"] == "10:25"
# 無期貨時需降低 coverage 並仍可運作
fl.volchart = lambda: (_ for _ in ()).throw(RuntimeError("blocked"))
r2 = fl.compute(dt.datetime.combine(day, dt.time(10, 45), ET), dt.time(10, 30)); print("無期貨:", r2["barometer"], r2["coverage"])
assert r2["coverage"] < 0.6
print("OK")
