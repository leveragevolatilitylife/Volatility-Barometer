# Volatility Barometer 模型檔

`Volatility_Barometer_model.xlsx` 是最新版模型（目前更新至 2026-11-12）。每週六更新後覆蓋此檔，歷史版本看 git log。

- 資料來源：`data/log.csv`、`data/raw_log.csv`、`data/daily_extras.csv`，以及 TWN-Stocks-Rotation-Strategy 的 `latest.xlsx`、stock-data-collection 的 `Stock_data_collection.xlsx`。
- VTS 實際 Barometer 欄位留空，由使用者自行填寫。
- `tools/` 是插入新列、延伸公式、打包 xlsx 的腳本（直接改 XML，避免圖表損毀）。
