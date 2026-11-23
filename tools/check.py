"""檢查 Wiki 與簡報（規則見 AGENTS.md 第 6 節）
用法：python tools/check.py [報告檔名]
"""
import json, re, sys, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, WIKI = ROOT / "raw", ROOT / "wiki"
OUTLINE = ROOT / "slides" / "outline.json"

UNITS = "年月日時分秒人級公里萬戶份次層天條弱強%"

def nums(text):
    """抓出「數字+單位」，例如 2,454 人 -> 2454人、9 秒 -> 9秒。
    第 1 次檢查時只比數字，S04 裡「9 月」的 9 讓「9 秒」誤判成有來源，所以改成連單位一起比。
    清單編號（1. 2. 3.）不算內容數字。"""
    text = re.sub(r"(?m)^\s*\d+\.\s", "", text)
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    out = set()
    for n, u in re.findall(r"(\d+(?:\.\d+)?)[ \t]*([^\s\d]?)", text):
        out.add(n + (u if u and u in UNITS else ""))
    return out

def strip_marks(text):
    """去掉來源標記 [S01] 與 [[連結]]，避免把它們的數字當成內容"""
    return re.sub(r"\[S\d+\]|\[\[[^\]]+\]\]", "", text)

raw_text = {p.name[:3]: p.read_text() for p in RAW.glob("S*.md")}
pages = {p.stem: p.read_text() for p in WIKI.glob("*.md") if p.stem not in ("index", "log")}
errors, passed = [], []

def check(code, ok_list, bad_list):
    (passed if not bad_list else errors).append((code, ok_list, bad_list))

# W1 來源標記存在而且 raw 有這份
bad = []
for name, txt in pages.items():
    tags = set(re.findall(r"\[(S\d+)\]", txt))
    if not tags:
        bad.append(f"{name}: 沒有任何來源標記")
    for t in tags - set(raw_text):
        bad.append(f"{name}: 用了 [{t}]，但 raw/ 沒有這份")
check("W1 來源標記", len(pages), bad)

# W2 [[連結]] 不斷
bad = []
for name, txt in list(pages.items()) + [("index", (WIKI / "index.md").read_text())]:
    for link in re.findall(r"\[\[([^\]]+)\]\]", txt):
        if link not in pages:
            bad.append(f"{name}: [[{link}]] 不存在")
check("W2 連結不斷", len(pages), bad)

# W3 index 列出所有頁
idx = (WIKI / "index.md").read_text()
bad = [f"index 沒列 {n}" for n in pages if f"[[{n}]]" not in idx]
check("W3 目錄完整", len(pages), bad)

# W4 每一行的數字，要出現在那一行標的來源裡
bad = []
for name, txt in pages.items():
    for line in txt.splitlines():
        tags = re.findall(r"\[(S\d+)\]", line)
        if not tags:
            continue
        src = "".join(raw_text.get(t, "") for t in tags)
        missing = nums(strip_marks(line)) - nums(src)
        if missing:
            bad.append(f"{name}: 「{line.strip()[:40]}…」的 {sorted(missing)} 在 {tags} 找不到")
check("W4 數字對得上來源", len(pages), bad)

# ---------- 簡報 ----------
slides = json.loads(OUTLINE.read_text()) if OUTLINE.exists() else []

def slide_text(s):
    parts = [s.get("title", ""), s.get("lead", "")] + s.get("bullets", [])
    for row in s.get("table", []):
        parts += row
    for q in s.get("quiz", []):
        parts += [q["q"], q["explain"]] + q["options"]
    return "\n".join(parts)

# S1 每張有標 wiki 頁且存在
bad = []
for s in slides:
    if s.get("kind") == "cover":
        continue
    refs = s.get("wiki", [])
    if not refs:
        bad.append(f"第 {s['id']} 張「{s['title']}」沒標 wiki 頁")
    for r in refs:
        if r not in pages:
            bad.append(f"第 {s['id']} 張用了 wiki/{r}.md，但這頁不存在")
check("S1 每張都有 wiki 來源", len(slides), bad)

# S2 數字要在對應 wiki 頁
bad = []
for s in slides:
    if s.get("kind") == "cover":
        continue
    wiki = "".join(pages.get(r, "") for r in s.get("wiki", []))
    missing = nums(slide_text(s)) - nums(strip_marks(wiki))
    if missing:
        bad.append(f"第 {s['id']} 張「{s['title']}」的數字 {sorted(missing)} 在 {s.get('wiki')} 找不到")
check("S2 數字對得上 wiki", len(slides), bad)

# S3 粗體重點詞要在 wiki 頁
bad = []
for s in slides:
    wiki = "".join(pages.get(r, "") for r in s.get("wiki", []))
    for term in re.findall(r"\*\*(.+?)\*\*", slide_text(s)):
        if term not in wiki:
            bad.append(f"第 {s['id']} 張的重點詞「{term}」在 {s.get('wiki')} 找不到")
check("S3 重點詞對得上 wiki", len(slides), bad)

# S4 每張最多 4 條、每條 40 字
bad = []
for s in slides:
    b = s.get("bullets", [])
    if len(b) > 4:
        bad.append(f"第 {s['id']} 張有 {len(b)} 條（上限 4）")
    for x in b:
        n = len(x.replace("**", ""))
        if n > 40:
            bad.append(f"第 {s['id']} 張有一條 {n} 字（上限 40）：{x[:20]}…")
check("S4 字數限制", len(slides), bad)

# S5 wiki 頁有 ⚠（來源說法不同），用到那頁的投影片也要把 ⚠ 留下來
#    （第 1 次語意檢查發現第 5 張把衝突吃掉，才加上這條）
bad = []
for s in slides:
    for r in s.get("wiki", []):
        warn = [l for l in pages.get(r, "").splitlines() if "⚠" in l]
        # 只有投影片用到 ⚠ 那一行的數字時才算（第 9 次檢查時第 6 張誤報，才改成這樣）
        used = any(nums(strip_marks(l)) & nums(slide_text(s)) for l in warn)
        if used and "⚠" not in slide_text(s) + s.get("note", ""):
            bad.append(f"第 {s['id']} 張用了 {r}，那頁有 ⚠ 來源說法不同，但投影片沒寫出來")
check("S5 來源衝突要保留", len(slides), bad)

# ---------- 報告 ----------
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
out = [f"# 檢查報告 {now}", "", f"- wiki 頁數：{len(pages)}　raw 來源：{len(raw_text)}　投影片：{len(slides)}", ""]
for code, n, bad in sorted(passed + errors):
    out.append(f"## {'✅' if not bad else '❌'} {code}（{len(bad)} 個問題）")
    out += [f"- {b}" for b in bad]
    out.append("")
total = sum(len(b) for _, _, b in errors)
out.append(f"**結果：{'全部通過' if total == 0 else f'共 {total} 個問題，需要修正後重跑'}**")
report = "\n".join(out)
print(report)
if len(sys.argv) > 1:
    (ROOT / "logs" / sys.argv[1]).write_text(report + "\n")
sys.exit(1 if total else 0)
