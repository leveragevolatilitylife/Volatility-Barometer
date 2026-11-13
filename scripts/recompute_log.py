"""一次性修正：log.csv 在 history.csv 之後的列，HV5/HV20 / Traders VRP / Simple VRP 曾用過期 SPXTR 序列。
以 SPY 比率近似 S&P 日報酬重算這些欄位與其下游（溫度計、策略部位）。用法：python scripts/recompute_log.py <hist 最後一日的 SPY 收盤>"""
import csv, os, sys, json, numpy as np, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import barometer_core as bc, fetch_live as fl
DATA = fl.DATA; spy_base = float(sys.argv[1])
hist = fl.read_history(); last = hist[-1]["date"]
cfg = json.load(open(os.path.join(DATA, "weights.json")))
W = {x["name"]: x["weight"] for x in cfg["metrics"]}; DR = {x["name"]: x["dir"] for x in cfg["metrics"]}
H = {k: np.array([float(r[k]) if r[k] != "" else np.nan for r in hist]) for k in W}
rows = list(csv.DictReader(open(os.path.join(DATA, "log.csv")))); cols = list(rows[0].keys())
spx = [float(r["SPXTR"]) for r in hist]; ak = [float(r["AK"]) for r in hist]
prev_spy = spy_base; low = False; days = sorted({r["date"] for r in rows if r["date"] > last})
close = {}   # date -> (spx level, spy close) from 16:00 rows (late=0)
f = lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 6)
for d in days:
    drs = [r for r in rows if r["date"] == d]
    for r in drs:
        spy = float(r["SPY"]) if r["SPY"] else None
        if spy is None: continue
        lvl = spx[-1] * spy / prev_spy
        series = np.array(spx + [lvl]); hv5, hv20 = bc.hv(series, 5), bc.hv(series, 20)
        r["HV5"], r["HV20"] = f(hv5), f(hv20)
        vix = float(r["VIX"]); r["Simple VRP"] = f(vix - hv20)
        vx = r["VX30 M1:M2"]
        if vx != "" and len(ak) >= 4:
            a = [float(vx) - hv5] + list(ak[-1:-5:-1]); r["Traders VRP"] = f((5*a[0]+4*a[1]+3*a[2]+2*a[3]+a[4]) / 15)
        else: r["Traders VRP"] = ""
        vals = {k: (float(r[k]) if r[k] != "" else float("nan")) for k in W}
        score, cov, _ = bc.barometer(vals, H, W, DR)
        px = fl.price_signal(np.array(spx), lvl)
        tail, ts = bc.tail_state(score, px if not np.isnan(px) else 0.5)
        dstate, low = bc.defensive_state(score, low)
        r.update(barometer=round(score, 4), coverage=round(cov, 3), defensive=dstate, tactical=bc.tactical_state(score), tail=tail,
                 price_signal=round(px, 4), tail_score=round(ts, 4), def_low=int(low))
        if r["slot"] == "16:00": c_lvl, c_spy = lvl, spy; c_vx = vx; c_hv5 = hv5
    if "c_lvl" in dir() and any(r["slot"] == "16:00" for r in drs):
        spx.append(c_lvl); prev_spy = c_spy
        ak.append(float(c_vx) - c_hv5 if c_vx != "" else float("nan"))
with open(os.path.join(DATA, "log.csv"), "w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=cols); wr.writeheader(); wr.writerows(rows)
sp = os.path.join(DATA, "state.json")
json.dump({"low": bool(low), "date": rows[-1]["date"]}, open(sp, "w"))
print("recomputed", sum(1 for r in rows if r["date"] > last), "rows")
