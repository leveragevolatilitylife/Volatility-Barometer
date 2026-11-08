#!/usr/bin/env python3
"""抓即時資料 → 計算溫度計 → 寫 data/live.json；--mode snapshot 另外把「開盤後一小時」的值追加到 data/snapshots.csv。
用法: python scripts/fetch_live.py --mode live|snapshot [--at 10:30] [--force]
只用標準函式庫 + numpy。"""
import argparse, csv, datetime as dt, json, os, sys, urllib.request
from zoneinfo import ZoneInfo
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import barometer_core as bc, calendar_us as cal
ET = ZoneInfo("America/New_York"); DATA = os.path.join(ROOT, "data")
UA = {"User-Agent": "Mozilla/5.0 (compatible; baro-bot/1.0)"}

def http(url, headers=None, tries=3):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={**UA, **(headers or {})})
            return urllib.request.urlopen(req, timeout=20).read().decode()
        except Exception as e:
            last = e
    raise RuntimeError(f"{url}: {last}")

def yahoo(sym, interval, rng):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym.replace('^','%5E')}?interval={interval}&range={rng}"
    r = json.loads(http(u))["chart"]["result"][0]
    ts = r["timestamp"]; q = r["indicators"]["quote"][0]
    return [(t, c) for t, c in zip(ts, q["close"]) if c is not None], r["meta"]

def asof(bars, limit_ts, day):
    """取 day (ET 日期) 內、時間戳 ≤ limit_ts 的最後一根。回傳 (價, 該根時間) 或 None。"""
    best = None
    for t, c in bars:
        if dt.datetime.fromtimestamp(t, ET).date() == day and t <= limit_ts: best = (c, t)
    return best

def volchart():
    j = json.loads(http("https://volchart.io/ajax_update", {"X-Requested-With": "XMLHttpRequest"}))
    px = []
    for i in range(8):
        last, bid, ask = j[2][i], j[4][i], j[6][i]
        v = last if last and last > 0 else ((bid + ask) / 2 if bid and ask else None)
        if v is None and j[5][i] and j[7][i]: v = None  # 無報價 → 缺值
        px.append(v)
    idx = {"VIX": j[8][0], "VIX3M": j[9][0], "VIX9D": j[10][0], "VIX6M": j[11][0]}
    return j[0], px, idx

def read_history():
    rows = list(csv.DictReader(open(os.path.join(DATA, "history.csv"))))
    return rows

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

def compute(now_et, snap_at):
    day = now_et.date()
    target = dt.datetime.combine(day, snap_at, ET)
    limit = int(target.timestamp()) - 300 if snap_at else int(now_et.timestamp()) - 300
    src = {}
    # 1) 指數：Yahoo 5 分 K（失敗則用 volchart 的即時值）
    vals = {}; stamp = None
    for key, sym in (("VIX", "^VIX"), ("VIX9D", "^VIX9D"), ("VIX3M", "^VIX3M"), ("VIX6M", "^VIX6M"), ("VOLI", "^VOLI")):
        try:
            bars, _ = yahoo(sym, "5m", "2d"); a = asof(bars, limit, day)
            if a: vals[key] = a[0]; stamp = max(stamp or 0, a[1]); src[key] = "yahoo"
        except Exception as e:
            src[key] = f"yahoo-fail:{str(e)[:60]}"
    # 2) 期貨 + 指數備援：volchart
    months = fut = None
    try:
        months, fut, vc = volchart()
        for k, v in vc.items():
            if k not in vals and v: vals[k] = v; src[k] = "volchart"
    except Exception as e:
        src["futures"] = f"volchart-fail:{str(e)[:60]}"
    need = ["VIX", "VIX9D", "VIX3M", "VIX6M"]
    if any(k not in vals for k in need): raise RuntimeError(f"缺少必要指數: {[k for k in need if k not in vals]}  {src}")
    hist = read_history()
    spxtr = np.array([float(r["SPXTR"]) for r in hist])
    # 3) S&P：用 ^GSPC 日內漲跌率推估今日 SPXTR
    gb, gm = yahoo("^GSPC", "5m", "2d"); ga = asof(gb, limit, day)
    gd, _ = yahoo("^GSPC", "1d", "3mo")
    prev_close = [c for t, c in gd if dt.datetime.fromtimestamp(t, ET).date() < day][-1]
    chg = ga[0] / prev_close - 1 if ga else 0.0
    last_hist_day = dt.date.fromisoformat(hist[-1]["date"])
    spx_today = spxtr[-1] * (1 + chg)  # 以最近一筆歷史收盤為基準（歷史應每日更新）
    series = np.append(spxtr, spx_today)
    hv5, hv20 = bc.hv(series, 5), bc.hv(series, 20)
    K, D, w, chain = cal.roll_weights(day)
    futs = None
    if fut and months:
        order = [m for (_, m, _) in chain]; name = {v: k for k, v in cal.MONTHS.items()}
        mp = {months[i]: fut[i] for i in range(len(months))}
        futs = [mp.get(name[m]) for m in order[:7]]
        if any(v is None for v in futs[:3]): futs = None
    akp = [float(r["AK"]) for r in hist[-4:]][::-1]
    m = bc.metrics_from_raw(vals["VIX"], vals["VIX9D"], vals["VIX3M"], vals["VIX6M"], vals.get("VOLI", float("nan")),
                            futs, w, hv5, hv20, akp)
    if "VOLI" not in vals: m["VIX-VOLI"] = float("nan")
    cfg = json.load(open(os.path.join(DATA, "weights.json")))
    W = {x["name"]: x["weight"] for x in cfg["metrics"]}; DR = {x["name"]: x["dir"] for x in cfg["metrics"]}
    H = {k: np.array([float(r[k]) if r[k] != "" else np.nan for r in hist]) for k in W}
    score, cov, detail = bc.barometer(m, H, W, DR)
    px = price_signal(spxtr, spx_today)
    tail, tail_s = bc.tail_state(score, px if not np.isnan(px) else 0.5)
    low = False
    st = os.path.join(DATA, "state.json")
    if os.path.exists(st): low = json.load(open(st)).get("low", False)
    dstate, low2 = bc.defensive_state(score, low)
    return {
        "asof_et": now_et.isoformat(timespec="seconds"), "trade_date": day.isoformat(),
        "bar_time_et": dt.datetime.fromtimestamp(stamp, ET).strftime("%H:%M") if stamp else None,
        "barometer": round(score, 4), "coverage": round(cov, 3), "price_signal": round(px, 4), "tail_score": round(tail_s, 4),
        "strategies": {"defensive": dstate, "tactical": bc.tactical_state(score), "tail": tail},
        "inputs": {**{k: v for k, v in vals.items()}, "HV5": hv5, "HV20": hv20, "roll_w": w, "K": K, "futures": futs},
        "metrics": detail, "sources": src, "_low": low2,
    }

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mode", default="live", choices=["live", "snapshot"])
    ap.add_argument("--at", default="10:30"); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    now = dt.datetime.now(ET); today = now.date()
    if a.mode == "snapshot":
        if not cal.is_trading_day(today): print("非交易日，略過"); return 0
        snap = dt.time.fromisoformat(a.at)
        if now.time() < (dt.datetime.combine(today, snap) + dt.timedelta(minutes=5)).time() and not a.force:
            print("尚未到時間，略過"); return 0
        path = os.path.join(DATA, "snapshots.csv")
        if os.path.exists(path) and any(l.startswith(today.isoformat()) for l in open(path)) and not a.force:
            print("今日已記錄"); return 0
        r = compute(now, snap)
    else:
        r = compute(now, None)
    low = r.pop("_low")
    if a.mode == "snapshot":
        path = os.path.join(DATA, "snapshots.csv"); new = not os.path.exists(path)
        cols = ["date", "bar_time_et", "barometer", "coverage", "defensive", "tactical", "tail", "price_signal", "tail_score",
                "VIX", "VIX9D", "VIX3M", "VIX6M", "VOLI", "HV5", "HV20"] + [x["name"] for x in json.load(open(os.path.join(DATA, "weights.json")))["metrics"]]
        row = [r["trade_date"], r["bar_time_et"], r["barometer"], r["coverage"], r["strategies"]["defensive"], r["strategies"]["tactical"],
               r["strategies"]["tail"], r["price_signal"], r["tail_score"]] + [r["inputs"].get(k, "") for k in ("VIX", "VIX9D", "VIX3M", "VIX6M", "VOLI", "HV5", "HV20")] + \
              [("" if v["value"] is None else round(v["value"], 6)) for v in r["metrics"].values()]
        with open(path, "a", newline="") as f:
            wr = csv.writer(f)
            if new: wr.writerow(cols)
            wr.writerow(row)
        json.dump({"low": low, "date": r["trade_date"]}, open(os.path.join(DATA, "state.json"), "w"))
        json.dump(r, open(os.path.join(DATA, "snapshot_latest.json"), "w"), ensure_ascii=False, default=float)
        print("snapshot recorded", r["trade_date"], r["barometer"])
    # intraday 軌跡（供網頁畫當日走勢）
    ip = os.path.join(DATA, "intraday_today.json")
    tr = json.load(open(ip)) if os.path.exists(ip) else {"date": "", "points": []}
    if tr["date"] != r["trade_date"]: tr = {"date": r["trade_date"], "points": []}
    tr["points"].append({"t": r["asof_et"][11:16], "b": r["barometer"], "cov": r["coverage"]}); tr["points"] = tr["points"][-120:]
    json.dump(tr, open(ip, "w")); json.dump(r, open(os.path.join(DATA, "live.json"), "w"), ensure_ascii=False, default=float, indent=1)
    print("ok", r["barometer"], r["strategies"]); return 0

if __name__ == "__main__":
    sys.exit(main())
