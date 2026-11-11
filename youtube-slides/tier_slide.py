"""画像などで渡されたTier表を、ランキングスライドと同じデザイン（make_slides.py のCSS）の1枚（1920×1080 PNG）にする。

ranking.json に無いTier表（過去の月のランキングなど）用。並び・ランク・キャラ名は youtube-slides/tiers/<名前>.json に書く
（元画像から読み取ったものをそのまま。推測で並べ替えたり足したりしない）。
キャラ名は chars.json の名前と完全一致していないと止まる。アイコンは pawa-data の event-chars/icons（PSR、無ければSR）。
使い方：python3 youtube-slides/tier_slide.py youtube-slides/tiers/sep2026.json [出力先フォルダ]
"""
import ast, json, re, subprocess, sys, tempfile, html as H
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
SPEC = Path(sys.argv[1])
DEST = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "out"
spec = json.load(open(SPEC))

# デザインは make_slides.py と同じものを使う（ファイルから FONT と CSS を取り出すだけ。実行はしない）
src = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse((HERE / "make_slides.py").read_text()).body
       if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ("FONT", "CSS")}
# ランクの色：make_slides.py の4色（SS/S/A/B）に、高校キャラ・Cを足す（上から 赤・橙・黄・緑・青 の順）
EXTRA = ".tier-hs{background:#ff6b6b}.tier-C{background:#74c0fc}"
CLS = {"高校キャラ": "hs"}

CHARS = {c["name"]: c for c in json.load(open(SITE.parent / "pawa-data/event-chars/chars.json"))}
ICONS = SITE.parent / "pawa-data/event-chars/icons"


def icon(c):
    base = f'{c["苗字"]}{c.get("名前") or ""}' + (f'_{c["二つ名"]}' if c.get("二つ名") else "")
    for rare in ("PSR", "SR"):
        f = ICONS / f"{base}_{rare}.png"
        if f.exists():
            return f.as_uri()
    sys.exit(f"アイコンが無い：{c['name']}")


rows = spec["rows"]
for t, names in rows:
    for n in names:
        assert n in CHARS, f"chars.json に無い名前：{n}"
MAXN = max(len(n) for _, n in rows)
FW = min(151, (1720 - 138 - 20) // MAXN)
# 行数が多いときは、行の高さ（962px ÷ 行数）に収まるようにアイコンを小さくする（名前2行ぶんの余白を残す）
# サブタイトル（"subtitle"、任意）があるときは、その分だけ表を下げる
SUB = spec.get("subtitle", "")
TOP = 150 if SUB else 108
TH = 1070 - TOP
ICON, NM, SM = min(128, FW - 20, TH // len(rows) - 92), round(26 * min(1, FW / 151), 1), round(18 * min(1, FW / 151), 1)

out = []
for t, names in rows:
    ics = ""
    for n in names:
        m = re.match(r"\[(.*?)\](.*)", n)
        small, name = (m.group(1), m.group(2)) if m else ("", n)
        # 「・」「=」の後ろで改行できるようにする
        segs = re.split(r"(?<=[・=])", name)
        ln = ' class="ln"' if len(segs) > 1 or len(name) > 8 else ""
        nm = "".join(f"<b>{H.escape(s)}</b>" for s in segs)
        sm = f"<small>[{H.escape(small)}]</small>" if small else ""
        ics += f'<div class="ic"><img src="{icon(CHARS[n])}">{sm}<span{ln}>{nm}</span></div>'
    label = "<br>".join(H.escape(x) for x in (["高校", "キャラ"] if t == "高校キャラ" else [t]))
    fs = 42 if t == "高校キャラ" else 72
    out.append(f'<div class="row"><div class="tier tier-{CLS.get(t, t)}" style="width:138px;font-size:{fs}px;line-height:1.15;text-align:center;white-space:nowrap">{label}</div><div class="ics">{ics}</div></div>')

sub = (f'<div class="title" style="top:96px;height:44px;line-height:44px;font-size:32px;font-weight:700;color:#5a6577">{H.escape(SUB)}</div>'
       if SUB else "")
body = (f'<div class="title">{H.escape(spec["title"])}</div>{sub}'
        f'<div class="tt" style="left:100px;top:{TOP}px;width:1720px;height:{TH}px;--icon:{ICON}px;--w:{FW}px;--nm:{NM}px;--sm:{SM}px;--pad:18px">'
        + "".join(out) + "</div>")
doc = (f'<!doctype html><html lang="ja"><head><meta charset="utf-8">{src["FONT"]}<style>{src["CSS"]}{EXTRA}</style></head>'
       f'<body>{body}<script>window.fit=()=>{{}}</script></body></html>')

DEST.mkdir(parents=True, exist_ok=True)
work = Path(tempfile.mkdtemp())
(work / "t.html").write_text(doc)
png = DEST / f"{SPEC.stem}_tier.png"
(work / "jobs.json").write_text(json.dumps([[str(work / "t.html"), str(png)]]))
subprocess.run(["node", str(HERE / "shot.js"), str(work / "jobs.json")], check=True)
print("できあがり:", png)
