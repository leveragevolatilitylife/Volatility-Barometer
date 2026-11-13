# 即時波動率溫度計 (Volatility Barometer Live)

靜態網頁 + GitHub Actions：每個美股交易日開盤後約 1 小時（10:30 ET）自動記錄溫度計與三策略部位到 `data/snapshots.csv`，
盤中另可手動／排程更新 `data/live.json`。

## 結構
- `index.html`, `assets/` 網頁（沿用站內風格；可放 `assets/avatar.jpg`）
- `scripts/barometer_core.py` 13 指標公式、百分位、加權、策略狀態（含 Defensive 磁滯）
- `scripts/calendar_us.py` 美股休市日與 VIX 期貨到期日
- `scripts/fetch_live.py` 抓資料（Yahoo 5 分 K：VIX/VIX9D/VIX3M/VIX6M/VOLI/GSPC；volchart.io：VIX 期貨 M1–M7）
- `data/history.csv` 歷史指標（百分位基準，到 2026-11-06）、`weights.json` 權重與門檻
- `.github/workflows/barometer.yml` 排程；`tests/` 驗證

## 記錄時段（美東時間）
09:30（開盤價）、10:00、10:30（作者決策時點）、11:00 … 15:30、16:00（收盤）＝每日 14 筆，寫入 `data/log.csv`。
每筆含：溫度計與覆蓋率、三策略部位、VIX/VIX9D/VIX3M/VIX6M/VOLI、HV5/HV20、**SVIX、SVXY、GLD、VXZ、QLD、QQQ、XLU、SPY、IYR、KO、CAOS 價格**、13 項指標原始值。
- 價格取法：09:30＝當日第一根 5 分 K 的開盤價；其餘＝時段前一根 5 分 K（起點 ≤ T−5 分）的收盤價；16:00＝當日最後一根收盤價。
- 因為 volchart 期貨約延遲 15 分鐘，時段 T 要到 T+16 分鐘（收盤 +20 分）才記錄。錯過超過 45 分鐘時仍會用 Yahoo 補記價格，但期貨類指標視為缺值（`late=1`，覆蓋率約 47%）——**回測請排除 `late=1` 或 `coverage<0.95` 的列**。
- 回測用法：以時段 T 的部位訊號，在同一時段（或下一時段）的標的價格建倉，與 `log.csv` 的收盤列比較，即可比較「盤中即時調倉」與「收盤才決定」的差異；`def_low` 為 Defensive 磁滯狀態。

## 網頁功能
- `index.html` 即時溫度計；`backtest.html` 在瀏覽器內以 `data/log.csv` 自動回測（開始日期、決策頻率、成交時點、成本、各策略基準下拉選單、決策時段比較）。
- 「↻ 立即更新資料」按鈕：用 GitHub API 觸發 workflow。首次按下會要求貼上 fine-grained token（僅限本 repo、Actions: Read and write），只存在該瀏覽器的 localStorage，不會上傳。
- Tail 中間區間的 IYR/KO：依 `data/rate_cycle.json`（最近一次 FOMC 調整方向：降息→IYR、升息→KO），workflow 每日嘗試由 FRED(DFEDTARU) 自動更新，取不到則沿用檔案內容；網頁可手動覆寫。
- 前端引擎 `assets/engine.js` 可用 node 單獨測試。

## 部署
1. 把整個資料夾放進 GitHub repo，Settings → Pages 選 main / root。
2. Settings → Actions → General → Workflow permissions 選 Read and write。
3. 準點觸發（強烈建議）：GitHub 內建 cron 常延遲，請用 cron-job.org 建 job：
   `POST https://api.github.com/repos/<帳號>/<repo>/actions/workflows/barometer.yml/dispatches`
   Header：`Authorization: Bearer <fine-grained PAT，僅該 repo 的 Actions 讀寫>`、`Accept: application/vnd.github+json`
   Body：`{"ref":"main","inputs":{"mode":"auto"}}`
   排程：時區 America/New_York，週一至五，09:46–16:56 每 10 分鐘（或每 30 分鐘的 :16 與 :46，另加 16:20）。腳本自動略過休市日與已記錄時段。

## 重要限制（請務必知道）
- volchart 的期貨報價約延遲 15 分鐘，所以快照在 10:45 ET 執行，指數取 ≤10:25 的 5 分 K，期貨取當下延遲報價。
- 期貨類指標約占 47% 權重；取不到時自動剔除並重新正規化，頁面顯示覆蓋率。
- 權重為由作者公開數據擬合；歷史重建 RMSE≈0.037、相關係數 0.986，不是官方數值。
- 工作表的「到期交易日」欄在 2024-12 之後與真實 CBOE 日曆不一致，本專案採真實日曆。
- Yahoo／volchart 為非官方來源，可能改版或封鎖 GitHub runner；失敗時 workflow 會報錯，不會寫入假資料。
- `history.csv` 目前不會自動延伸（百分位基準固定到 2026-11-06）；長期使用建議每月補一次。
- `tests/demo/` 僅為版面測試用的假資料，以 `index.html?data=tests/demo` 預覽，勿當真。

## 測試
`python tests/test_core.py`（需原始 df2.pkl）、`python tests/test_fetch_mock.py`（離線管線）。
- `data/raw_log.csv`：同時段另存原始值（M1–M7、VIX1Y、VVIX、SKEW、SPXTR、SPX），供每週更新 Excel 用（SDEX/TDEX 無免費來源，未記錄）。
