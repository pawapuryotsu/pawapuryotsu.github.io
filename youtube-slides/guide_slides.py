"""ランキングの解説欄（評価基準・加点要素など、箇条書きの見出し）を YouTube 動画用スライド（1920×1080 PNG）にする。
ランキングスライド（make_slides.py）と同じデザイン。文章は src/ranking/ranking.json の「解説欄」をそのまま使う（言い換えない）。
1行に収まらない項目は、文字を少し（50pxまで）小さくして1行に収める。{赤太:…} などの色指示はサイトと同じ色で出す（charpages.py の rich を使う）。

使い方：python3 youtube-slides/guide_slides.py <ランキングのキー> [出力先フォルダ] [--all]
  既定は箇条書きのある見出しだけ（評価基準・加点要素）。--all で文章の見出し（評価理由詳細など）も作る。
  見出し1つにつき1枚。出力は <キー>_guide/guide_1.png …（ファイル名は英数字だけ）
"""
import json, re, subprocess, shutil, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
sys.path.insert(0, str(SITE))
from charpages import rich, e  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
ALL = "--all" in sys.argv
KEY = args[0] if args else "roman"
DEST = Path(args[1]) if len(args) > 1 else HERE / "out"
rank = json.load(open(SITE / "src/ranking/ranking.json"))["ranking"][KEY]
TITLE = rank["title"]

FONT = '<link href="https://fonts.googleapis.com/css2?family=M+PLUS+1p:wght@500;700;800;900&display=swap" rel="stylesheet">'
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1920px;height:1080px;overflow:hidden;background:#eaeeea;font-family:'M PLUS 1p',sans-serif;color:#14233a}
.title{position:absolute;left:0;right:0;top:8px;height:100px;text-align:center;font-weight:900;font-size:76px;line-height:100px;letter-spacing:2px;color:#14233a;white-space:nowrap}
.panel{position:absolute;left:100px;top:118px;width:1720px;height:942px;background:#fff;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,.08);padding:40px 60px;overflow:hidden}
.panel h2{font-weight:900;font-size:64px;line-height:1.2;padding-left:26px;border-left:14px solid #2e7d32;margin-bottom:24px;white-space:nowrap}
.body{font-size:var(--fs);font-weight:800;line-height:1.45}
.body ul{list-style:none}
.body li{position:relative;padding:.32em 0 .32em 1.1em;border-top:2px solid #e3e6ea}
.body li:first-child{border-top:none}
.body li::before{content:"";position:absolute;left:.2em;top:calc(.32em + .5em);width:.42em;height:.42em;border-radius:50%;background:#2e7d32}
.body p{margin:0 0 .6em}
.tx-r{color:#c62828}.tx-b{color:#1565c0}.tx-bold{font-weight:900}
"""
FIT_JS = """<script>window.fit=()=>{const t=document.querySelector('.title');let s=76;while(t.scrollWidth>t.clientWidth&&s>40){s-=2;t.style.fontSize=s+'px'}
const pn=document.querySelector('.panel'),b=pn.querySelector('.body');let f=58;b.style.setProperty('--fs',f+'px');
const wraps=()=>[...b.querySelectorAll('li')].some(li=>li.getBoundingClientRect().height>f*1.45*1.8);
while(wraps()&&f>50){f-=2;b.style.setProperty('--fs',f+'px')}
while(pn.scrollHeight>pn.clientHeight+1&&f>28){f-=2;b.style.setProperty('--fs',f+'px')}};</script>"""

WORK = Path(tempfile.mkdtemp())
OUT = DEST / f"{KEY}_guide"
OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob("*.png"):
    f.unlink()
jobs, order = [], []
for g in rank.get("解説欄", []):
    if not g.get("箇条書き") and not ALL:
        continue
    body = ""
    if g.get("箇条書き"):
        body += "<ul>" + "".join(f"<li>{rich(x)}</li>" for x in g["箇条書き"]) + "</ul>"
    body += "".join(f"<p>{rich(x)}</p>" for x in g.get("文章", []))
    head = re.sub(r"^【(.*)】$", r"\1", g["見出し"])
    n = len(jobs) + 1
    fn = WORK / f"{n}.html"
    fn.write_text(f'<!doctype html><html><head><meta charset="utf-8">{FONT}<style>{CSS}</style>{FIT_JS}</head><body>'
                  f'<div class="title">{e(TITLE)}</div><div class="panel"><h2>{e(head)}</h2><div class="body">{body}</div></div></body></html>')
    jobs.append([str(fn), str(OUT / f"guide_{n}.png")])
    order.append(f"guide_{n}.png  {g['見出し']}")
(WORK / "jobs.json").write_text(json.dumps(jobs))
subprocess.run(["node", str(HERE / "shot.js"), str(WORK / "jobs.json")], check=True)
(OUT / "order.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
shutil.rmtree(WORK)
print("\n".join(order))
print("できあがり:", OUT)
