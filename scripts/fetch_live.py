#!/usr/bin/env python3
"""抓即時資料 → 計算溫度計 → 寫 data/live.json，並把「開盤、每半小時、收盤」的時段記錄追加到 data/log.csv。

時段 (美東)：09:30(開盤價)、10:00、10:30、…、15:30、16:00(收盤)。共 14 筆/日。
  - 指數與 11 檔標的：Yahoo 5 分 K。時段 T 取「K 線起點 ≤ T−5 分」的最後一根收盤價；09:30 取當日第一根開盤價；16:00 取當日最後一根收盤價。
  - VIX 期貨：volchart.io（CBOE 延遲約 15 分鐘），所以時段 T 要等到 T+16 分鐘（收盤 +20 分）才記錄，期貨報價才對得上 T。
  - 若錯過時段太久 (> T+45 分)，仍會用 Yahoo 補記，但期貨類指標視為缺值（late=1），避免把錯誤時間的期貨報價寫進去。
用法: python scripts/fetch_live.py [--mode auto|live] [--force]   (auto：補記到期時段 + 更新 live.json)"""
import argparse, csv, datetime as dt, json, os, sys, urllib.request
from zoneinfo import ZoneInfo
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import barometer_core as bc, calendar_us as cal
ET = ZoneInfo("America/New_York"); DATA = os.path.join(ROOT, "data")
UA = {"User-Agent": "Mozilla/5.0 (compatible; baro-bot/1.0)"}
SLOTS = ["09:30"] + [f"{h:02d}:{m:02d}" for h in range(10, 16) for m in (0, 30)] + ["16:00"]
TICKERS = ["SVIX", "SVXY", "GLD", "VXZ", "QLD", "QQQ", "XLU", "SPY", "IYR", "KO", "CAOS"]
INDEX_SYMS = (("VIX", "^VIX"), ("VIX9D", "^VIX9D"), ("VIX3M", "^VIX3M"), ("VIX6M", "^VIX6M"), ("VOLI", "^VOLI"))
FUT_LAG_MIN, LATE_MIN = 16, 45

def http(url, headers=None, tries=3):
    last = None
    for _ in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}), timeout=20).read().decode()
        except Exception as e:
            last = e
    raise RuntimeError(f"{url}: {last}")

class Ctx:
    """單次執行內的快取：每個代號只抓一次。"""
    def __init__(self):
        self.bars = {}; self.daily = {}; self.vc = None; self.err = {}
    def get_bars(self, sym):
        if sym not in self.bars:
            try:
                u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym.replace('^','%5E')}?interval=5m&range=5d"
                r = json.loads(http(u))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
                # 只留常規時段 09:30–16:15 ET（^VIX 等指數自 03:15 起就有盤前 K 線，不能把它當開盤價）
                inrth = lambda t: dt.time(9, 30) <= local(t).time() <= dt.time(16, 15)
                self.bars[sym] = [(t, o, c) for t, o, c in zip(r["timestamp"], q["open"], q["close"]) if c is not None and o is not None and inrth(t)]
            except Exception as e:
                self.bars[sym] = []; self.err[sym] = str(e)[:80]
        return self.bars[sym]
    def get_daily(self, sym):
        if sym not in self.daily:
            try:
                u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym.replace('^','%5E')}?interval=1d&range=3mo"
                r = json.loads(http(u))["chart"]["result"][0]
                self.daily[sym] = [(dt.datetime.fromtimestamp(t, ET).date(), c) for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c is not None]
            except Exception as e:
                self.daily[sym] = []; self.err[sym + "_1d"] = str(e)[:80]
        return self.daily[sym]
    def get_vc(self):
        if self.vc is None:
            try:
                j = json.loads(http("https://volchart.io/ajax_update", {"X-Requested-With": "XMLHttpRequest"}))
                px = []
                for i in range(8):
                    last, bid, ask = j[2][i], j[4][i], j[6][i]
                    px.append(last if last and last > 0 else ((bid + ask) / 2 if bid and ask else None))
                self.vc = (j[0], px, {"VIX": j[8][0], "VIX3M": j[9][0], "VIX9D": j[10][0], "VIX6M": j[11][0]})
            except Exception as e:
                self.vc = False; self.err["volchart"] = str(e)[:80]
        return self.vc or None

def local(t): return dt.datetime.fromtimestamp(t, ET)

def slot_price(bars, day, slot):
    """回傳 (價格, K 線起點時間戳)。slot: 'LIVE' | '09:30' | 'HH:MM' | '16:00'。"""
    db = [b for b in bars if local(b[0]).date() == day]
    if not db: return None
    if slot == "LIVE" or slot == "16:00": return db[-1][2], db[-1][0]
    if slot == "09:30": return db[0][1], db[0][0]
    h, m = map(int, slot.split(":")); lim = int(dt.datetime.combine(day, dt.time(h, m), ET).timestamp()) - 300
    ok = [b for b in db if b[0] <= lim]
    return (ok[-1][2], ok[-1][0]) if ok else None

def price_signal(spx_hist, today_level):
    """S&P 價格訊號 = 5 項指標「1−歷史百分位」平均（回撤252、5日報酬、20日報酬、距50/200日均線）。"""
    s = np.append(np.asarray(spx_hist, float), today_level)
    def feats(a):
        n = len(a); f = np.full((5, n), np.nan)
        for i in range(n):
            if i >= 252: f[0, i] = a[i] / a[i - 252:i + 1].max() - 1
            if i >= 5: f[1, i] = a[i] / a[i - 5] - 1
            if i >= 20: f[2, i] = a[i] / a[i - 20] - 1
            if i >= 49: f[3, i] = a[i] / a[i - 49:i + 1].mean() - 1
            if i >= 199: f[4, i] = a[i] / a[i - 199:i + 1].mean() - 1
        return f
    f = feats(s[-1500:]); ranks = []
    for k in range(5):
        p = bc.percentile(f[k, -1], f[k, :-1])
        if not np.isnan(p): ranks.append(1 - p)
    return float(np.mean(ranks)) if ranks else float("nan")

def read_history():
    return list(csv.DictReader(open(os.path.join(DATA, "history.csv"))))

def compute(ctx, day, slot, now_et, low_flag=False, allow_futures=True):
    src = {}; vals = {}; stamp = None
    for key, sym in INDEX_SYMS:
        a = slot_price(ctx.get_bars(sym), day, slot)
        if a: vals[key] = a[0]; stamp = max(stamp or 0, a[1]); src[key] = "yahoo"
    months = fut = None
    if allow_futures:
        vc = ctx.get_vc()
        if vc:
            months, fut, idx = vc
            for k, v in idx.items():
                if k not in vals and v: vals[k] = v; src[k] = "volchart"
    need = ["VIX", "VIX9D", "VIX3M", "VIX6M"]
    if any(k not in vals for k in need): raise RuntimeError(f"缺少必要指數 {[k for k in need if k not in vals]} err={ctx.err}")
    prices = {}
    for t in TICKERS:
        a = slot_price(ctx.get_bars(t), day, slot)
        prices[t] = round(a[0], 4) if a else None
    hist = read_history(); spxtr = np.array([float(r["SPXTR"]) for r in hist])
    ga = slot_price(ctx.get_bars("^GSPC"), day, slot)
    prev = [c for d, c in ctx.get_daily("^GSPC") if d < day]
    chg = ga[0] / prev[-1] - 1 if ga and prev else 0.0
    if day <= dt.date.fromisoformat(hist[-1]["date"]):
        spx_today = spxtr[-1]; series = spxtr; base = spxtr[:-1]
    else:
        spx_today = spxtr[-1] * (1 + chg); series = np.append(spxtr, spx_today); base = spxtr
    hv5, hv20 = bc.hv(series, 5), bc.hv(series, 20)
    K, D, w, chain = cal.roll_weights(day)
    futs = None
    if fut and months:
        name = {v: k for k, v in cal.MONTHS.items()}; mp = {months[i]: fut[i] for i in range(len(months))}
        futs = [mp.get(name[m]) for (_, m, _) in chain[:7]]
        if any(v is None for v in futs[:3]): futs = None
    akp = [float(r["AK"]) for r in hist[-4:]][::-1]
    m = bc.metrics_from_raw(vals["VIX"], vals["VIX9D"], vals["VIX3M"], vals["VIX6M"], vals.get("VOLI", float("nan")), futs, w, hv5, hv20, akp)
    if "VOLI" not in vals: m["VIX-VOLI"] = float("nan")
    cfg = json.load(open(os.path.join(DATA, "weights.json")))
    W = {x["name"]: x["weight"] for x in cfg["metrics"]}; DR = {x["name"]: x["dir"] for x in cfg["metrics"]}
    H = {k: np.array([float(r[k]) if r[k] != "" else np.nan for r in hist]) for k in W}
    score, cov, detail = bc.barometer(m, H, W, DR)
    px = price_signal(base, spx_today)
    tail, tail_s = bc.tail_state(score, px if not np.isnan(px) else 0.5)
    dstate, low2 = bc.defensive_state(score, low_flag)
    return {"asof_et": now_et.isoformat(timespec="seconds"), "trade_date": day.isoformat(), "slot": slot,
            "bar_time_et": local(stamp).strftime("%H:%M") if stamp else None,
            "barometer": round(score, 4), "coverage": round(cov, 3), "price_signal": round(px, 4), "tail_score": round(tail_s, 4),
            "strategies": {"defensive": dstate, "tactical": bc.tactical_state(score), "tail": tail}, "def_low": int(low2),
            "prices": prices, "inputs": {**vals, "HV5": hv5, "HV20": hv20, "roll_w": w, "K": K, "futures": futs},
            "metrics": detail, "sources": src, "errors": ctx.err}

LOG_FIXED = ["date", "slot", "bar_time_et", "late", "barometer", "coverage", "defensive", "tactical", "tail", "price_signal", "tail_score", "def_low",
             "VIX", "VIX9D", "VIX3M", "VIX6M", "VOLI", "HV5", "HV20"]
def log_cols():
    return LOG_FIXED + TICKERS + [x["name"] for x in json.load(open(os.path.join(DATA, "weights.json")))["metrics"]]

def log_row(r, late):
    f = lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else (round(v, 6) if isinstance(v, float) else v)
    return [r["trade_date"], r["slot"], r["bar_time_et"], int(late), r["barometer"], r["coverage"], r["strategies"]["defensive"], r["strategies"]["tactical"],
            r["strategies"]["tail"], r["price_signal"], r["tail_score"], r["def_low"]] + \
           [f(r["inputs"].get(k)) for k in ("VIX", "VIX9D", "VIX3M", "VIX6M", "VOLI", "HV5", "HV20")] + \
           [f(r["prices"].get(t)) for t in TICKERS] + [f(v["value"]) for v in r["metrics"].values()]

def logged(path, day):
    if not os.path.exists(path): return set()
    return {r["slot"] for r in csv.DictReader(open(path)) if r["date"] == day.isoformat()}

def write_live(r):
    ip = os.path.join(DATA, "intraday_today.json")
    tr = json.load(open(ip)) if os.path.exists(ip) else {"date": "", "points": []}
    if tr["date"] != r["trade_date"]: tr = {"date": r["trade_date"], "points": []}
    tr["points"].append({"t": r["asof_et"][11:16], "b": r["barometer"], "cov": r["coverage"]}); tr["points"] = tr["points"][-200:]
    json.dump(tr, open(ip, "w")); json.dump(r, open(os.path.join(DATA, "live.json"), "w"), ensure_ascii=False, default=float, indent=1)

def update_rate_cycle():
    """從 FRED (DFEDTARU，聯邦基金目標區間上限) 更新升/降息事件；取不到就保留現有檔案。每日最多一次。"""
    p = os.path.join(DATA, "rate_cycle.json"); cur = json.load(open(p)) if os.path.exists(p) else {"events": []}
    today = dt.date.today().isoformat()
    if cur.get("checked") == today: return
    try:
        txt = http("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARU&cosd=2022-01-01")
        prev = None; ev = []
        for ln in txt.strip().splitlines()[1:]:
            d, v = ln.split(",")[:2]
            if v in (".", ""): continue
            v = float(v)
            if prev is not None and abs(v - prev) > 1e-9: ev.append({"date": d, "dir": "hike" if v > prev else "cut", "range": f"{v-0.25:.2f}-{v:.2f}"})
            prev = v
        if ev:
            old = [e for e in cur["events"] if e["date"] < "2022-01-01"]
            cur["events"] = old + ev; cur["source"] = "FRED DFEDTARU"
        cur["checked"] = today; cur["updated"] = today
        json.dump(cur, open(p, "w"), ensure_ascii=False, indent=1); print("rate_cycle updated", ev[-1:] )
    except Exception as e:
        print("rate_cycle skipped:", str(e)[:80])

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mode", default="auto", choices=["auto", "live"]); ap.add_argument("--force", action="store_true")
    a = ap.parse_args(); now = (dt.datetime.fromisoformat(os.environ['BARO_NOW']).replace(tzinfo=ET) if os.environ.get('BARO_NOW') else dt.datetime.now(ET)); today = now.date(); ctx = Ctx(); path = os.path.join(DATA, "log.csv")
    done = 0
    update_rate_cycle()
    if a.mode == "auto" and cal.is_trading_day(today):
        have = logged(path, today); sp = os.path.join(DATA, "state.json")
        state = json.load(open(sp)) if os.path.exists(sp) else {}
        low = bool(state.get("low", False)) if state.get("date", "") <= today.isoformat() else False
        for s in SLOTS:
            if s in have: continue
            h, m = map(int, s.split(":")); t0 = dt.datetime.combine(today, dt.time(h, m), ET)
            lag = 20 if s == "16:00" else FUT_LAG_MIN
            if now < t0 + dt.timedelta(minutes=lag): break
            late = now > t0 + dt.timedelta(minutes=LATE_MIN + (4 if s == "16:00" else 0))
            try:
                r = compute(ctx, today, s, now, low, allow_futures=not late)
            except Exception as e:
                print("slot", s, "failed:", e); continue
            low = bool(r["def_low"]); new = not os.path.exists(path)
            with open(path, "a", newline="") as f:
                wr = csv.writer(f)
                if new: wr.writerow(log_cols())
                wr.writerow(log_row(r, late))
            json.dump({"low": low, "date": today.isoformat()}, open(sp, "w")); done += 1
            print("logged", s, r["barometer"], "late" if late else "")
    # live.json：盤中 (09:25–16:40 ET) 或手動 / 尚無檔案時更新
    live_p = os.path.join(DATA, "live.json")
    in_hours = cal.is_trading_day(today) and dt.time(9, 25) <= now.time() <= dt.time(16, 40)
    if a.mode == "live" or a.force or in_hours or not os.path.exists(live_p):
        eff = today
        if not (cal.is_trading_day(today) and now.time() >= dt.time(9, 30)):
            days = sorted({local(t).date() for t, _, _ in ctx.get_bars("^GSPC")})
            eff = days[-1] if days else today
        r = compute(ctx, eff, "LIVE", now, False); r.pop("def_low", None); write_live(r)
        print("live", r["trade_date"], r["barometer"], r["strategies"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
