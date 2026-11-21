"""西球記「虹特の査定まとめ」ページ（src/pages/pawaque-saikyuki-niji.html）を YouTube 動画用スライド（1920×1080 PNG）にする。
ランキングスライドと同じデザイン。文章・表・色はページのものをそのまま使う（言い換えない）。
使い方：python3 youtube-slides/niji_slides.py [出力先フォルダ] → <出力先>/niji/niji_01.png … と order.txt
ページを直したら、このスクリプトを流し直せばスライドも同じ内容になる。
"""
import re, json, subprocess, shutil, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
DEST = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out"
src = (SITE / "src/pages/pawaque-saikyuki-niji.html").read_text(encoding="utf-8")
src = src.replace("{{root}}", (SITE / "docs").as_uri() + "/")
lead = re.search(r'<section class="phead">.*?<p>(.*?)</p></section>', src, re.S).group(1)
body = src.split("</nav>", 1)[1].split("<!-- SKNAV:START -->")[0]
blocks, cur = [], []
for l in body.split("\n"):
    if re.match(r"^  <(?!/)", l) and cur:
        blocks.append("\n".join(cur)); cur = []
    cur.append(l)
blocks.append("\n".join(cur))
blocks = [b for b in blocks if b.strip() and not b.strip().startswith("<!--")]
def text(i): return re.sub(r"<[^>]+>", "", blocks[i]).strip()
def find(s):
    hit = [i for i in range(len(blocks)) if text(i).startswith(s)]
    assert len(hit) == 1, (s, hit); return hit[0]
def exact(s):
    hit = [i for i in range(len(blocks)) if text(i) == s]
    assert len(hit) == 1, (s, hit); return hit[0]
def after(s, n):  # 見出し s の次から n ブロック
    i = exact(s) if s in HEADS else find(s); return list(range(i + 1, i + 1 + n))

HEADS = {"野手の虹特の査定", "投手の虹特の査定"}
TITLE = "パワクエ西球記 虹特の査定まとめ"
# (パネル見出し, ブロック番号, 追加クラス)
how = find("調べ方")
SLIDES = [
    ("調べ方", after("調べ方", 2), ""),
    ("調べ方（例：先発の鋼が真・精密機械に進化）", list(range(how + 3, how + 9)), "shots"),
    ("調べ方", list(range(how + 9, how + 11)), ""),
    ("調べ方", [how + 11], ""),
    ("野手の虹特の査定", after("野手の虹特の査定", 2), ""),
    ("投手の虹特の査定", after("投手の虹特の査定", 2), ""),
    ("虹特に進化できる対戦相手（野手）", [find("どの虹特に"), exact("野手の虹特") + 1], ""),
    ("虹特に進化できる対戦相手（投手）", [find("どの虹特に"), exact("投手の虹特") + 1], ""),
    ("チームランク更新を狙う上で意識する事", after("チームランク更新を狙う上で", 3), ""),
    ("伝授してから進化させるなら「合計」で比べる", after("伝授してから進化させるなら", 1), ""),
    ("候補が5個以上だとランダムになる", after("候補が5個以上だと", 2), ""),
    ("必ず取りきれる伝授", after("候補が5個以上だと", 4)[2:], ""),
    ("必ず取りきれる順番（1〜3回目）", after("候補が5個以上だと", 5)[4:], ""),
    ("必ず取りきれる順番（4〜8回目）", after("3回目が「怪童×2", 1), "cap1"),
    ("必ず取りきれる順番（4〜8回目）", after("3回目が「怪童×3", 1), "cap2"),
    ("必ず取りきれる順番（9〜11回目）", after("9回目からは", 1), "cap3"),
    ("中継ぎ・抑えには怪童・金縛りを伝授しない", after("中継ぎ・抑えには", 1), ""),
    ("中継ぎ・抑えには怪童・金縛りを伝授しない", after("中継ぎ・抑えには", 2)[1:], ""),
    ("ベンチ野手はいつもどおりでOK", after("ベンチ野手はいつもどおり", 1), ""),
    ("あくまで理論上の話になる", after("あくまで理論上", 1), ""),
    ("あくまで理論上の話になる", after("あくまで理論上", 3)[1:], ""),
]
CAPS = {"cap1": "3回目が「怪童×2、アーチスト×2」の時", "cap2": "3回目が「怪童×3、アーチスト×1」の時", "cap3": "9回目からはどちらも同じ"}

FONT = '<link href="https://fonts.googleapis.com/css2?family=M+PLUS+1p:wght@500;700;800;900&display=swap" rel="stylesheet">'
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1920px;height:1080px;overflow:hidden;background:#eaeeea;font-family:'M PLUS 1p',sans-serif;color:#14233a}
.title{position:absolute;left:0;right:0;top:8px;height:100px;text-align:center;font-weight:900;font-size:76px;line-height:100px;letter-spacing:2px;white-space:nowrap}
.panel{position:absolute;left:100px;top:118px;width:1720px;height:942px;background:#fff;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,.08);padding:40px 60px;overflow:hidden}
.panel h2{font-weight:900;font-size:60px;line-height:1.2;padding-left:26px;border-left:14px solid #2e7d32;margin-bottom:24px;white-space:nowrap}
.body{font-size:var(--fs);font-weight:800;line-height:1.5}
.body p{margin:0 0 .5em}.body ul{list-style:none;margin:0 0 .5em}
.body li{position:relative;padding:.25em 0 .25em 1.1em;border-top:2px solid #e3e6ea}.body li:first-child{border-top:none}
.body li::before{content:"";position:absolute;left:.2em;top:calc(.25em + .55em);width:.42em;height:.42em;border-radius:50%;background:#2e7d32}
.body h3,.body h2{display:none}
.em-blue{color:#1a5fd0;font-weight:900}.em-red{color:#d6303a;font-weight:900}.tx-red{color:#d6303a}.tx-b{color:#1565c0}
.cp-nw{white-space:nowrap}
.body table{width:100%;border-collapse:collapse;margin:.2em 0 .5em}
.body th,.body td{border:2px solid #d5dbe3;padding:.18em .45em;text-align:center;vertical-align:middle;line-height:1.3}
.body thead th{background:#24324a;color:#fff;font-size:.8em}
.body tbody th{text-align:left;background:#f3f6f9;white-space:nowrap}
.body td.nj-op{text-align:left;font-weight:700}
.nj-d{font-size:.65em;color:#555;font-weight:700}
.pq-cap{font-weight:900;margin:.3em 0 .2em}
.cover .panel{display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}
.cover h1{font-size:120px;font-weight:900;line-height:1.3}.cover h1 small{display:block;font-size:64px;color:#2e7d32}
.cover p{font-size:52px;font-weight:800;margin-top:50px;line-height:1.6}
.body td br{display:none}.body tbody td:first-child,.body tbody td:nth-child(2){white-space:nowrap}.body td .nj-d{margin-left:.5em}
.shots .body{display:grid;grid-template-columns:1fr 1fr;grid-template-areas:"c1 c2" "i1 i2" "c3 i2" "i3 i2" "x i2";grid-template-rows:auto auto auto auto 1fr;column-gap:50px;font-size:40px}
.shots .body>:nth-child(1){grid-area:c1}.shots .body>:nth-child(2){grid-area:i1}.shots .body>:nth-child(3){grid-area:c2}.shots .body>:nth-child(4){grid-area:i2}.shots .body>:nth-child(5){grid-area:c3}.shots .body>:nth-child(6){grid-area:i3}
.shots .body img{width:100%;height:auto;display:block;border:2px solid #d5dbe3}
"""
FIT_JS = """<script>window.fit=()=>{const t=document.querySelector('.title');let s=76;while(t.scrollWidth>t.clientWidth&&s>40){s-=2;t.style.fontSize=s+'px'}
const pn=document.querySelector('.panel'),h=pn.querySelector('h2'),b=pn.querySelector('.body');if(!b)return;
let hs=60;while(h.scrollWidth>h.clientWidth&&hs>36){hs-=2;h.style.fontSize=hs+'px'}
if(document.body.classList.contains('shots'))return;
let f=64;b.style.setProperty('--fs',f+'px');
while((pn.scrollHeight>pn.clientHeight+1||pn.scrollWidth>pn.clientWidth+1)&&f>24){f-=2;b.style.setProperty('--fs',f+'px')}};</script>"""

def page(cls, inner):
    return (f'<!doctype html><html><head><meta charset="utf-8">{FONT}<style>{CSS}</style>{FIT_JS}</head>'
            f'<body class="{cls}"><div class="title">{TITLE}</div>{inner}</body></html>')

WORK = Path(tempfile.mkdtemp())
OUT = DEST / "niji"
OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob("*.png"): f.unlink()
pages = [("表紙", page("cover", f'<div class="panel"><h1><small>パワクエ 西球記</small>虹特の査定まとめ</h1><p>{lead}</p></div>'))]
for head, idx, cls in SLIDES:
    if cls == "shots":
        imgs = [blocks[i] for i in idx]
        inner = "".join(imgs)
        pages.append((head, page("shots", f'<div class="panel"><h2>{head}</h2><div class="body">{inner}</div></div>')))
        continue
    cap = f'<p class="pq-cap">{CAPS[cls]}</p>' if cls in CAPS else ""
    pages.append((head, page(cls, f'<div class="panel"><h2>{head}</h2><div class="body">{cap}{"".join(blocks[i] for i in idx)}</div></div>')))
jobs, order = [], []
for n, (head, html) in enumerate(pages, 1):
    fn = WORK / f"{n}.html"; fn.write_text(html, encoding="utf-8")
    jobs.append([str(fn), str(OUT / f"niji_{n:02d}.png")]); order.append(f"niji_{n:02d}.png  {head}")
(WORK / "jobs.json").write_text(json.dumps(jobs))
subprocess.run(["node", str(HERE / "shot.js"), str(WORK / "jobs.json")], check=True)
(OUT / "order.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
shutil.rmtree(WORK)
print("\n".join(order)); print("できあがり:", OUT)
