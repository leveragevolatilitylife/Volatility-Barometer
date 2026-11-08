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

## 部署
1. 把整個資料夾放進一個 GitHub repo（例如 `Volatility-Barometer`），Settings → Pages 選 main / root。
2. Settings → Actions → General → Workflow permissions 選 Read and write。
3. 準點觸發（建議）：GitHub 內建 cron 常延遲數小時，請用 cron-job.org 建 job：
   `POST https://api.github.com/repos/<帳號>/<repo>/actions/workflows/barometer.yml/dispatches`
   Header：`Authorization: Bearer <fine-grained PAT，僅該 repo 的 Actions 讀寫>`、`Accept: application/vnd.github+json`
   Body：`{"ref":"main","inputs":{"mode":"snapshot"}}`
   排程：週一至五、美東時間 10:45（時區選 America/New_York，自動處理夏令）。腳本會自行略過休市日與重複記錄。
4. 盤中即時更新：同法再建一個 job（`"mode":"live"`，每 15 分鐘，美東 9:35–16:00）。

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
