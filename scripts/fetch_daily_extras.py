"""抓每日收盤的補充序列（S&P 500 Total Return、VVIX、SKEW、VIX1Y、VOLI、SPX、SDEX、TDEX），近 3 個月，存 data/daily_extras.csv。
供每週更新 Excel 用實際收盤值（SPXTR 含股息，不可用 SPY 推算）。"""
import os, sys, csv, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import fetch_live as fl
SYMS = (("SPXTR", "^SP500TR"), ("VVIX", "^VVIX"), ("SKEW", "^SKEW"), ("VIX1Y", "^VIX1Y"), ("VOLI", "^VOLI"), ("SPX", "^GSPC"), ("SDEX", "^SDEX"), ("TDEX", "^TDEX"))
ctx = fl.Ctx(); data = {}
for k, s in SYMS:
    for d, c in ctx.get_daily(s): data.setdefault(d, {})[k] = c
if ctx.err: print("errors:", ctx.err)
with open(os.path.join(fl.DATA, "daily_extras.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date"] + [k for k, _ in SYMS])
    for d in sorted(data): w.writerow([d.isoformat()] + [round(data[d][k], 4) if k in data[d] else "" for k, _ in SYMS])
print("rows", len(data))
