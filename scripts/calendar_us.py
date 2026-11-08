"""美股交易日曆與 VIX 期貨到期日（只用標準函式庫）。"""
import datetime as dt

def _nth_weekday(y, m, wd, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(wd - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)

def _last_weekday(y, m, wd):
    d = dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - wd) % 7)

def _easter(y):
    a = y % 19; b, c = divmod(y, 100); d, e = divmod(b, 4)
    f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7; m = (a + 11 * h + 22 * l) // 451
    mo = (h + l - 7 * m + 114) // 31; da = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(y, mo, da)

def _observed(d):
    if d.weekday() == 5: return d - dt.timedelta(days=1)
    if d.weekday() == 6: return d + dt.timedelta(days=1)
    return d

def holidays(y):
    h = {_observed(dt.date(y, 1, 1)), _nth_weekday(y, 1, 0, 3), _nth_weekday(y, 2, 0, 3),
         _easter(y) - dt.timedelta(days=2), _last_weekday(y, 5, 0), _observed(dt.date(y, 7, 4)),
         _nth_weekday(y, 9, 0, 1), _nth_weekday(y, 11, 3, 4), _observed(dt.date(y, 12, 25))}
    if y >= 2022: h.add(_observed(dt.date(y, 6, 19)))
    return h

def is_trading_day(d):
    return d.weekday() < 5 and d not in holidays(d.year) and not (d.month == 12 and d.day == 31 and d.weekday() == 4 and False)

def prev_trading_day(d):
    d -= dt.timedelta(days=1)
    while not is_trading_day(d): d -= dt.timedelta(days=1)
    return d

def vix_expiry(y, m):
    """VIX 月合約 (y, m) 到期日：下個月第三個週五往前 30 天（週三）；遇休市日往前一個交易日。"""
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    fri = _nth_weekday(ny, nm, 4, 3)
    if not is_trading_day(fri): fri = prev_trading_day(fri)
    exp = fri - dt.timedelta(days=30)
    while not is_trading_day(exp): exp -= dt.timedelta(days=1)
    return exp

MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

def contract_chain(today, n=8):
    """從 today 起，到期日 > today 的連續 n 個 VIX 月合約 [(y, m, expiry)]（M1 為第一個）。
    與使用者工作表一致：到期當日即視為已換到下一個合約。"""
    y, m = today.year, today.month
    out = []
    while len(out) < n:
        e = vix_expiry(y, m)
        if e > today: out.append((y, m, e))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out

def tdays_between(a, b):
    """a、b 之間（不含兩端）的交易日數。"""
    n, d = 0, a + dt.timedelta(days=1)
    while d < b:
        n += is_trading_day(d); d += dt.timedelta(days=1)
    return n

def roll_weights(today):
    """回傳 (K, D, w, chain)：K=今日到 M1 到期日之間的交易日數（不含兩端），
    D=前一檔到期日到 M1 到期日之間的交易日數+1，w=K/D。"""
    chain = contract_chain(today)
    m1 = chain[0]
    prev = vix_expiry(*((m1[0] - 1, 12) if m1[1] == 1 else (m1[0], m1[1] - 1)))
    K = tdays_between(today, m1[2])
    D = tdays_between(prev, m1[2]) + 1   # 與使用者工作表一致：w = K/(D+1)
    return K, D, min(max(K / D, 0.0), 1.0), chain
