"""把 wiki/、raw/ 轉成網頁，並把 slides/outline.json 生成 slides/index.html
用法：python tools/build.py
"""
import json, re, html, pathlib, markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, WIKI, SLIDES = ROOT / "raw", ROOT / "wiki", ROOT / "slides"
esc = html.escape

CSS = """
:root{--bg:#f6f4ef;--ink:#1d2430;--muted:#5b6472;--line:#ddd8cc;--card:#fff;--accent:#d9480f;--accent2:#1c4e80}
@media (prefers-color-scheme:dark){:root{--bg:#14181f;--ink:#e9ecf1;--muted:#a3acb9;--line:#2c3340;--card:#1b2029;--accent:#ff7a45;--accent2:#7fb2e5}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.75 "Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:28px 20px 60px}
a{color:var(--accent2)}header.top{display:flex;gap:16px;align-items:center;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:20px}
header.top b{color:var(--accent)}header.top a{text-decoration:none}
h1{font-size:1.7rem;line-height:1.35;margin:.2em 0 .4em}h2{font-size:1.2rem;margin-top:1.8em;border-left:4px solid var(--accent);padding-left:10px}
blockquote{margin:0 0 1em;padding:12px 16px;background:var(--card);border:1px solid var(--line);border-radius:10px;font-weight:600}
table{border-collapse:collapse;width:100%;background:var(--card);font-size:.95rem}td,th{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}th{background:color-mix(in srgb,var(--accent) 10%,var(--card))}
code{background:var(--card);padding:1px 5px;border-radius:4px}.src{font-size:.8em;color:var(--muted);text-decoration:none;white-space:nowrap}
.wl{background:color-mix(in srgb,var(--accent2) 12%,transparent);padding:1px 6px;border-radius:6px;text-decoration:none}
"""

def page(title, body, depth=1):
    up = "../" * depth
    nav = (f'<header class="top"><b>地震防災 LLM Wiki</b><a href="{up}wiki/index.html">Wiki 目錄</a>'
           f'<a href="{up}slides/index.html">教學簡報</a><a href="{up}wiki/log.html">工作紀錄</a></header>')
    return (f'<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>'
            f'<style>{CSS}</style></head><body><div class="wrap">{nav}{body}</div></body></html>')

raw_files = {p.name[:3]: p for p in sorted(RAW.glob("S*.md"))}

def fix_blank_lines(text):
    """markdown 需要空行分段：引用、來源、相關、表格結束後都補一個空行"""
    out, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        out.append(line)
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.startswith((">", "來源：", "相關：", "- 來源：")) and nxt.strip():
            out.append("")
        elif line.startswith("|") and nxt.strip() and not nxt.startswith("|"):
            out.append("")
    return "\n".join(out)

def md_to_html(text):
    text = fix_blank_lines(text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r'<a class="wl" href="\1.html">\1</a>', text)
    text = re.sub(r"\[(S\d+)\]", lambda m: f'<a class="src" href="../raw/{raw_files[m[1]].stem}.html">[{m[1]}]</a>'
                  if m[1] in raw_files else m[0], text)
    return markdown.markdown(text, extensions=["tables"])

def title_of(text):
    return text.splitlines()[0].lstrip("# ").strip()

# --- wiki 與 raw 轉 HTML ---
for folder in (WIKI, RAW):
    for md in folder.glob("*.md"):
        t = md.read_text()
        (folder / f"{md.stem}.html").write_text(page(title_of(t), md_to_html(t)))

# --- 首頁 ---
(ROOT / "index.html").write_text(page("地震防災 LLM Wiki", """
<h1>地震防災 LLM Wiki × 教學簡報</h1>
<blockquote>用 LLM Wiki 整理 10 份地震防災資料，再從 Wiki 生成給初學者的教學簡報。</blockquote>
<p>👉 <a href="slides/index.html"><b>看教學簡報</b></a>（鍵盤 ← → 或滑動換頁）</p>
<p>📚 <a href="wiki/index.html">看 Wiki 目錄</a>　🗒 <a href="wiki/log.html">看工作紀錄（ingest／檢查／重生成）</a></p>
<p>流程：取得資料（raw/）→ 查詢 Wiki → 整理重點（slides/outline.json）→ 檢查（tools/check.py）→ 產生簡報（tools/build.py）</p>
""", depth=0))

# --- 簡報 ---
pages = {p.stem: p.read_text() for p in WIKI.glob("*.md")}
slides = json.loads((SLIDES / "outline.json").read_text())

def rich(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))

def wiki_links(refs):
    return "、".join(f'<a href="../wiki/{r}.html">{esc(title_of(pages[r]))}</a>' for r in refs)

parts = []
for s in slides:
    k = s.get("kind", "content")
    inner = ""
    if k == "cover":
        inner = (f'<div class="cover"><div class="tag">地震防災入門</div><h1>{rich(s["title"])}</h1>'
                 f'<p class="lead">{rich(s["lead"])}</p><p class="hint">按 → 或往左滑開始</p></div>')
    else:
        inner += f'<h2>{rich(s["title"])}</h2>'
        if s.get("lead"):
            inner += f'<p class="lead">{rich(s["lead"])}</p>'
        if s.get("table"):
            head, *rows = s["table"]
            inner += '<table><thead><tr>' + "".join(f"<th>{rich(c)}</th>" for c in head) + "</tr></thead><tbody>"
            inner += "".join("<tr>" + "".join(f"<td>{rich(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>"
        if k == "steps":
            inner += '<ol class="steps">' + "".join(f"<li>{rich(b)}</li>" for b in s["bullets"]) + "</ol>"
        elif s.get("bullets"):
            inner += "<ul>" + "".join(f"<li>{rich(b)}</li>" for b in s["bullets"]) + "</ul>"
        if k == "quiz":
            for qi, q in enumerate(s["quiz"]):
                opts = "".join(f'<button data-ok="{int(i == q["answer"])}">{esc(o)}</button>' for i, o in enumerate(q["options"]))
                inner += (f'<div class="q"><p><b>Q{qi + 1}.</b> {esc(q["q"])}</p><div class="opts">{opts}</div>'
                          f'<p class="ans" hidden>{esc(q["explain"])}</p></div>')
        if k == "sources":
            inner += '<h3>資料來源（全部先收進 Wiki，再做成簡報）</h3><ol class="srcs">'
            for sid, p in raw_files.items():
                t = p.read_text()
                url = re.search(r"網址：(\S+)", t)[1]
                org = re.search(r"來源：(.+)", t)[1]
                inner += f'<li><a href="{esc(url)}">{esc(org)}</a></li>'
            inner += "</ol>"
        if s.get("note"):
            inner += f'<p class="note">{rich(s["note"])}</p>'
        inner += f'<footer>Wiki 來源：{wiki_links(s["wiki"])}</footer>'
    parts.append(f'<section class="slide {k}" data-id="{s["id"]}">{inner}</section>')

DECK_CSS = """
:root{--bg:#f6f4ef;--ink:#1d2430;--muted:#5b6472;--line:#ddd8cc;--card:#fff;--accent:#d9480f;--accent2:#1c4e80}
@media (prefers-color-scheme:dark){:root{--bg:#14181f;--ink:#e9ecf1;--muted:#a3acb9;--line:#2c3340;--card:#1b2029;--accent:#ff7a45;--accent2:#7fb2e5}}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;overflow:hidden}
.deck{height:100%;display:flex;align-items:center;justify-content:center;padding:16px}
.slide{display:none;width:min(1000px,100%);max-height:calc(100vh - 90px);overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:clamp(22px,4vw,52px);box-shadow:0 10px 30px rgba(0,0,0,.06)}
.slide.on{display:block;animation:in .25s ease}@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1}}
h1{font-size:clamp(2rem,6vw,3.6rem);margin:.2em 0;line-height:1.2}h2{font-size:clamp(1.4rem,3.6vw,2.2rem);margin:0 0 .5em;border-left:8px solid var(--accent);padding-left:14px;line-height:1.3}
h3{font-size:1.05rem;color:var(--muted);margin:1.2em 0 .3em}
.lead{font-size:clamp(1.05rem,2.4vw,1.35rem);color:var(--muted);margin:.2em 0 1em}
ul,ol{font-size:clamp(1.05rem,2.6vw,1.5rem);line-height:1.7;padding-left:1.3em;margin:.4em 0}li{margin:.25em 0}strong{color:var(--accent)}
table{border-collapse:collapse;width:100%;font-size:clamp(.95rem,2.3vw,1.3rem);margin:.4em 0 1em}td,th{border:1px solid var(--line);padding:.5em .7em;text-align:left}th{background:color-mix(in srgb,var(--accent) 12%,var(--card))}
ol.steps{list-style:none;padding:0;display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
ol.steps li{background:color-mix(in srgb,var(--accent) 9%,var(--card));border-radius:14px;padding:18px;margin:0;font-size:clamp(1.05rem,2.4vw,1.35rem)}
.cover{text-align:center;padding:4vh 0}.cover .tag{display:inline-block;background:var(--accent);color:#fff;border-radius:99px;padding:4px 16px;font-weight:700}
.hint{color:var(--muted);margin-top:2.5em}
.note{background:color-mix(in srgb,#f5a623 16%,var(--card));border-radius:10px;padding:10px 14px;font-size:.98rem;line-height:1.6}
footer{margin-top:1.4em;padding-top:.7em;border-top:1px dashed var(--line);font-size:.85rem;color:var(--muted)}footer a{color:var(--accent2)}
.q{margin:.8em 0}.q p{font-size:clamp(1rem,2.3vw,1.25rem);margin:.2em 0}.opts{display:flex;flex-wrap:wrap;gap:8px}
.opts button{font:inherit;font-size:1rem;padding:8px 14px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}
.opts button.right{background:#2b8a3e;color:#fff;border-color:#2b8a3e}.opts button.wrong{background:#c92a2a;color:#fff;border-color:#c92a2a}
.ans{color:var(--muted)}ol.srcs{font-size:.82rem;line-height:1.5;columns:2;column-gap:28px}ol.srcs li{break-inside:avoid}@media (max-width:700px){ol.srcs{columns:1}}
.bar{position:fixed;left:0;top:0;height:5px;background:var(--accent);transition:width .2s}
.ctl{position:fixed;bottom:12px;right:14px;display:flex;gap:8px;align-items:center;color:var(--muted);font-size:.9rem}
.ctl button{font:inherit;width:42px;height:42px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer;font-size:1.1rem}
.home{position:fixed;bottom:18px;left:16px;font-size:.85rem;color:var(--muted)}.home a{color:var(--muted)}
"""
DECK_JS = """
const S=[...document.querySelectorAll('.slide')],bar=document.querySelector('.bar'),num=document.querySelector('#num');
let i=Math.max(0,Math.min(S.length-1,(parseInt(location.hash.slice(1))||1)-1));
function go(n){i=Math.max(0,Math.min(S.length-1,n));S.forEach((s,k)=>s.classList.toggle('on',k===i));
bar.style.width=((i+1)/S.length*100)+'%';num.textContent=(i+1)+' / '+S.length;history.replaceState(null,'','#'+(i+1));}
document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();go(i+1)}if(['ArrowLeft','PageUp'].includes(e.key))go(i-1)});
document.querySelector('#prev').onclick=()=>go(i-1);document.querySelector('#next').onclick=()=>go(i+1);
let x0=null;document.addEventListener('touchstart',e=>x0=e.touches[0].clientX,{passive:true});
document.addEventListener('touchend',e=>{if(x0===null)return;const d=e.changedTouches[0].clientX-x0;if(Math.abs(d)>50)go(i+(d<0?1:-1));x0=null});
document.querySelectorAll('.q').forEach(q=>q.querySelectorAll('button').forEach(b=>b.onclick=()=>{
q.querySelectorAll('button').forEach(x=>x.classList.remove('right','wrong'));b.classList.add(b.dataset.ok==='1'?'right':'wrong');
q.querySelector('.ans').hidden=false;q.querySelector('.ans').textContent=(b.dataset.ok==='1'?'答對！':'再想想：')+q.querySelector('.ans').dataset.t}));
document.querySelectorAll('.ans').forEach(a=>a.dataset.t=a.textContent);
go(i);
"""
deck = (f'<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>地震來了怎麼辦？｜地震防災教學簡報</title><style>{DECK_CSS}</style></head><body>'
        f'<div class="bar"></div><main class="deck">{"".join(parts)}</main>'
        f'<div class="home"><a href="../index.html">首頁</a>・<a href="../wiki/index.html">Wiki</a></div>'
        f'<div class="ctl"><span id="num"></span><button id="prev" aria-label="上一張">←</button><button id="next" aria-label="下一張">→</button></div>'
        f'<script>{DECK_JS}</script></body></html>')
(SLIDES / "index.html").write_text(deck)
print(f"wiki {len(list(WIKI.glob('*.html')))} 頁、raw {len(raw_files)} 份、簡報 {len(slides)} 張 → 完成")
