# 地震防災 LLM Wiki × 教學簡報（生成式 AI 作業十）

- 教學簡報：https://s114213507-rgb.github.io/quake-wiki/slides/
- Wiki 目錄：https://s114213507-rgb.github.io/quake-wiki/wiki/index.html
- 工作紀錄：https://s114213507-rgb.github.io/quake-wiki/wiki/log.html

## 資料夾
- `AGENTS.md`：給 AI 的 Wiki 維護規則
- `raw/`：10 份原始資料摘要（S01–S10）
- `wiki/`：9 個知識頁 + `index.md` + `log.md`
- `slides/outline.json`：從 Wiki 整理出的簡報大綱；`slides/index.html`：生成的簡報
- `tools/check.py`：檢查 Wiki 與簡報；`tools/build.py`：產生網頁
- `logs/`：每次檢查的報告（run1–run14、語意檢查、瀏覽器測試）
- `docs/loop.png`：流程圖

## 流程
取得資料 → Ingest 進 Wiki →（檢查 A）→ 查詢 Wiki → 整理重點 →（檢查 B）→ 產生簡報 →（檢查 C）

```
python tools/check.py      # 檢查
python tools/build.py      # 產生網頁
```
