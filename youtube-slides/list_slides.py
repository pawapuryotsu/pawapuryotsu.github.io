"""YouTube動画用の「イベキャラ一覧」スライド（1920×1080 PNG）を作る。
ランキングスライド（make_slides.py）と同じデザイン。列は アイコン／キャラ名／実装日／入手手段。

データは pawa-data の chars.json（実装日・入手方法）とアイコン（event-chars/icons）から取る（推測で値を入れない）。
実装日が空欄のキャラは載せられないので、名前を表示して知らせる。

使い方：
  python3 youtube-slides/list_slides.py --since 2026/09/05 --title "タイトル" \
      [--exclude "[キャプテン]御幸一也" ...] [--until 2026/11/30] [--name 出力名] [出力先フォルダ]
  1枚に入るのは最大7人。多いときは自動で2枚目以降に分ける。
"""
import argparse, json, subprocess, shutil, tempfile, html as H
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "pawa-data" / "event-chars"
PER = 7

ap = argparse.ArgumentParser()
ap.add_argument("dest", nargs="?", default=str(HERE / "out"))
ap.add_argument("--since", required=True)
ap.add_argument("--until", default="9999/99/99")
ap.add_argument("--title", required=True)
ap.add_argument("--exclude", nargs="*", default=[])
ap.add_argument("--name", default="list")
a = ap.parse_args()

chars = json.load(open(DATA / "chars.json"))
names = {c["name"] for c in chars}
for x in a.exclude:
    assert x in names, f"chars.json に無い名前です: {x}"
nodate = [c["name"] for c in chars if not c.get("実装日")]
pick = sorted((c for c in chars if c.get("実装日") and a.since <= c["実装日"] <= a.until and c["name"] not in a.exclude),
              key=lambda c: c["実装日"])  # 同じ日は chars.json の並び


def icon(c):
    base = f'{c["苗字"]}{c.get("名前") or ""}' + (f'_{c["二つ名"]}' if c.get("二つ名") else "")
    for rare in ("PSR", "SR"):
        f = DATA / "icons" / f"{base}_{rare}.png"
        if f.exists():
            return f.as_uri()
    return None


FONT = '<link href="https://fonts.googleapis.com/css2?family=M+PLUS+1p:wght@500;700;800;900&display=swap" rel="stylesheet">'
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1920px;height:1080px;overflow:hidden;background:#eaeeea;font-family:'M PLUS 1p',sans-serif;color:#14233a}
.title{position:absolute;left:0;right:0;top:8px;height:100px;text-align:center;font-weight:900;font-size:76px;line-height:100px;letter-spacing:2px;color:#14233a;white-space:nowrap}
.tt{position:absolute;left:100px;top:118px;width:1720px;max-height:942px;background:#fff;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,.08);overflow:hidden;display:flex;flex-direction:column}
.hd,.row{display:grid;grid-template-columns:240px 1fr 400px 400px;align-items:center}
.hd{flex:none;height:76px;background:#14233a;color:#fff;font-weight:900;font-size:36px;text-align:center}
.row{flex:none;height:var(--rh);border-top:2px solid #e3e6ea;text-align:center}
.row:nth-child(odd){background:#f6f8f6}
.row img,.noimg{width:var(--ic);height:var(--ic);border-radius:12px;display:block;margin:auto;background:#f3e7c2}
.nm{text-align:left;padding-left:30px;line-height:1.2}
.nm .one{display:block;font-size:54px;font-weight:900;white-space:nowrap}
.nm .one small{font-size:1em;font-weight:900}
.nm.two .one small{display:block;font-size:30px;color:#666;font-weight:500}
.dt{font-size:50px;font-weight:900;letter-spacing:1px}
.ob{font-size:46px;font-weight:900}
.ob.ev{color:#c62828}.ob.ga{color:#1565c0}
"""
FIT_JS = """<script>window.fit=()=>{const t=document.querySelector('.title');let s=76;while(t.scrollWidth>t.clientWidth&&s>40){s-=2;t.style.fontSize=s+'px'}
document.querySelectorAll('.nm .one').forEach(el=>{if(el.scrollWidth>el.clientWidth)el.parentNode.classList.add('two');let s=54;while(el.scrollWidth>el.clientWidth&&s>30){s-=2;el.style.fontSize=s+'px'}})};</script>"""


def e(s):
    return H.escape(s)


def slide(part, title):
    rh = min(144, (1080 - 118 - 20 - 76) // max(len(part), 1))
    ic = rh - 18
    rows = ""
    for c in part:
        img = icon(c)
        im = f'<img src="{img}">' if img else '<div class="noimg"></div>'
        sub = f'<small>[{e(c["二つ名"])}]</small>' if c.get("二つ名") else ""
        nm = e(c["苗字"] + (c.get("名前") or ""))
        ob = c.get("入手方法") or "ガチャ"
        cls = "ev" if ob == "イベント報酬" else "ga"
        rows += (f'<div class="row"><div>{im}</div><div class="nm"><span class="one">{sub}{nm}</span></div>'
                 f'<div class="dt">{e(c["実装日"])}</div><div class="ob {cls}">{e(ob)}</div></div>')
    return (f'<!doctype html><html><head><meta charset="utf-8">{FONT}<style>{CSS}</style>{FIT_JS}</head>'
            f'<body style="--rh:{rh}px;--ic:{ic}px"><div class="title">{e(title)}</div>'
            f'<div class="tt"><div class="hd"><div>アイコン</div><div>キャラ名</div><div>実装日</div><div>入手手段</div></div>{rows}</div></body></html>')


WORK = Path(tempfile.mkdtemp())
DEST = Path(a.dest)
DEST.mkdir(parents=True, exist_ok=True)
parts = [pick[i:i + PER] for i in range(0, len(pick), PER)] or [[]]
jobs = []
for i, part in enumerate(parts, 1):
    fn = WORK / f"{i}.html"
    fn.write_text(slide(part, a.title))
    out = DEST / (f"{a.name}.png" if len(parts) == 1 else f"{a.name}_{i}.png")
    jobs.append([str(fn), str(out)])
(WORK / "jobs.json").write_text(json.dumps(jobs))
subprocess.run(["node", str(HERE / "shot.js"), str(WORK / "jobs.json")], check=True)
shutil.rmtree(WORK)
for c in pick:
    print(c["実装日"], c["name"], c.get("入手方法") or "ガチャ")
if nodate:
    print("実装日が空欄で載せられなかったキャラ:", "、".join(nodate))
print("できあがり:", ", ".join(j[1] for j in jobs))
