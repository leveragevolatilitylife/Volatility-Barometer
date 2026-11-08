"""波動率溫度計核心計算（純 Python + numpy，無網路依賴）。
13 項指標 → 歷史百分位 → 加權平均 → 三策略狀態。"""
import json, math
import numpy as np

# (欄名, 方向 'hi'=高=風險 / 'lo'=低=風險)
METRICS = [
    ("Cash VIX Oscillator", "lo"), ("Adjust M1:M2 VIX Futures", "lo"), ("VX30:VIX Roll Yield", "lo"),
    ("Traders VRP", "lo"), ("VIX-VOLI", "hi"), ("M1:M2 VIX Futures", "lo"), ("M4:M7 VIX Futures", "lo"),
    ("VIX9D:VIX", "hi"), ("VIX:VIX3M", "hi"), ("VIX:VIX6M", "hi"), ("Simple VRP", "hi"),
    ("VX30 M1:M2", "hi"), ("VIX (1 month)", "hi"),
]
FUTURES_BASED = {"Adjust M1:M2 VIX Futures", "VX30:VIX Roll Yield", "Traders VRP", "M1:M2 VIX Futures",
                 "M4:M7 VIX Futures", "VX30 M1:M2"}  # 需要期貨資料 (Traders VRP 含 VX30)

def hv(closes, n):
    """最近 n 個日報酬（含今日）的樣本標準差 × √252 × 100。closes 需含 n+1 筆以上，最後一筆為今日。"""
    c = np.asarray(closes, float)[-(n + 1):]
    r = c[1:] / c[:-1] - 1
    return float(np.std(r, ddof=1) * math.sqrt(252) * 100) if len(r) == n else float("nan")

def percentile(x, hist, min_obs=250):
    """x 在歷史 hist（不含今日）中的百分位；樣本少於 min_obs 回傳 nan。"""
    h = np.asarray(hist, float); h = h[~np.isnan(h)]
    if len(h) < min_obs or np.isnan(x): return float("nan")
    less = (h < x).sum(); eq = (h == x).sum()
    return float((less + (eq + 2) / 2) / (len(h) + 1))

def metrics_from_raw(vix, vix9d, vix3m, vix6m, voli, fut=None, w=None, hv5=None, hv20=None, ak_prev=None):
    """原始報價 → 13 指標。fut: M1..M7 (list, 可為 None)；w: 滾動權重 K/D；
    ak_prev: 前 4 日 AK(=VX30−HV5) 由新到舊 [AK1..AK4]（Traders VRP 用）。回傳 dict，缺資料者為 nan。"""
    nan = float("nan")
    m = {
        "Cash VIX Oscillator": -vix9d - vix + vix3m + vix6m,
        "VIX9D:VIX": vix9d / vix, "VIX:VIX3M": vix / vix3m, "VIX:VIX6M": vix / vix6m,
        "VIX-VOLI": vix - voli, "VIX (1 month)": vix,
        "Simple VRP": vix - hv20 if hv20 is not None else nan,
    }
    for k in ("Adjust M1:M2 VIX Futures", "VX30:VIX Roll Yield", "Traders VRP", "M1:M2 VIX Futures",
              "M4:M7 VIX Futures", "VX30 M1:M2"):
        m[k] = nan
    if fut is not None and w is not None and all(v is not None and v > 0 for v in fut[:3]):
        M = fut
        I = M[0] * w + M[1] * (1 - w); J = M[1] * w + M[2] * (1 - w)
        m["Adjust M1:M2 VIX Futures"] = J / I - 1
        m["M1:M2 VIX Futures"] = M[1] / M[0] - 1
        m["VX30:VIX Roll Yield"] = I / vix - 1
        m["VX30 M1:M2"] = I
        if len(M) >= 7 and M[3] and M[6]:
            m["M4:M7 VIX Futures"] = M[6] / M[3] - 1
        if hv5 is not None and ak_prev is not None and len(ak_prev) == 4:
            ak0 = I - hv5; a = [ak0] + list(ak_prev)
            m["Traders VRP"] = (5 * a[0] + 4 * a[1] + 3 * a[2] + 2 * a[3] + 1 * a[4]) / 15
        m["_vx30"] = I
    return m

def barometer(vals, hists, weights, directions):
    """vals: {metric: 今日值}；hists: {metric: 歷史序列}。
    回傳 (score, coverage, detail)。缺值指標自動剔除並對剩餘權重重新正規化。"""
    num = den = 0.0; detail = {}
    for k, w in weights.items():
        p = percentile(vals.get(k, float("nan")), hists[k])
        if not np.isnan(p):
            r = p if directions[k] == "hi" else 1 - p
            num += w * r; den += w
        else:
            r = None
        detail[k] = {"value": None if np.isnan(vals.get(k, float("nan"))) else float(vals[k]), "risk": r}
    tot = sum(weights.values())
    return (num / den if den > 0 else float("nan")), den / tot, detail

# ---- 策略狀態 ----
def defensive_state(b, low_flag=False, lo=0.20, re=0.30):
    """磁滯版：b<20% 進入「低波動 Cash」，需升至 ≥30% 才解除；
    未鎖定時：≥85% Cash；66–85% XLU；其餘 QLD。回傳 (state, low_flag)。"""
    if b < lo: low_flag = True
    elif b >= re: low_flag = False
    if low_flag: return "Cash", low_flag
    return ("Cash" if b >= 0.85 else ("XLU" if b >= 0.66 else "QLD")), low_flag

def tactical_state(b):
    return "SVIX" if b < 0.60 else ("GLD" if b < 0.95 else "VXZ")

def tail_state(b, px_signal):
    s = 0.8 * b + 0.2 * px_signal
    return ("SPY" if s < 0.60 else ("IYR/KO" if s < 0.90 else "CAOS")), s

def load_weights(path):
    d = json.load(open(path))
    return {m["name"]: m["weight"] for m in d["metrics"]}, {m["name"]: m["dir"] for m in d["metrics"]}
