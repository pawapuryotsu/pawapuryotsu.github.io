"""Tier表（youtube-slides/tiers/<名前>.json）のキャラを、ランクごとの表スライド（1920×1080 PNG）にする。

列：キャラ（アイコン＋名前）／前後（イベント前後）／基礎合計（PSR50・Lv35）／コツボナ（PSR50・Lv35）／推奨Lv
- 基礎合計＝筋力・敏捷・技術・変化球・精神ボーナスの合計（サイトのTier表メーカーと同じ）。コツボナ＝コツイベントボーナス
- 値は chars.json の「表示」（Lvの値＋覚醒＋固有）を使う
  - PSR50：PSRの表示（SR覚醒・PSR覚醒・固有を全部含む）のLv50の値
  - Lv35 ：SRの表示（SR覚醒・固有を含み、PSR覚醒は含まない）のLv35の値
  （管理人指示 2026-11-11：PSR50は覚醒をすべて含める。Lv35はPSR覚醒を含めず、SR覚醒は含める）
- 推奨Lv：基礎合計とコツボナが両方ともPSR50の値に届く一番低いLv。SR（35/37/40/45）で届けばその数字、
  SRでは届かずPSRで届くなら「PSR」＋Lv（Lv50はPSRでしかなれないので「50」）
- 1枚に最大 --max 人（既定7）。多いランクは半分ずつに分ける（Bランク①②など）
使い方：python3 youtube-slides/table_slides.py youtube-slides/tiers/next_batter.json [出力先フォルダ] [--max 7]
"""
import ast, json, math, re, subprocess, sys, tempfile, html as H
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
args = [a for a in sys.argv[1:]]
MAX = 7
if "--max" in args:
    i = args.index("--max"); MAX = int(args[i + 1]); del args[i:i + 2]
SPEC = Path(args[0])
DEST = Path(args[1]) if len(args) > 1 else HERE / "out"
spec = json.load(open(SPEC))

src = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse((HERE / "make_slides.py").read_text()).body
       if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ("FONT", "CSS")}

CHARS = {c["name"]: c for c in json.load(open(SITE.parent / "pawa-data/event-chars/chars.json"))}
ICONS = SITE.parent / "pawa-data/event-chars/icons"
BASE = ["筋力ボーナス", "敏捷ボーナス", "技術ボーナス", "変化球ボーナス", "精神ボーナス"]
COLOR = {"SS": "#ff6b6b", "S": "#ffa94d", "A": "#ffe066", "B": "#a9e34b", "C": "#74c0fc", "高校キャラ": "#ff6b6b"}


def icon(c):
    base = f'{c["苗字"]}{c.get("名前") or ""}' + (f'_{c["二つ名"]}' if c.get("二つ名") else "")
    for rare in ("PSR", "SR"):
        f = ICONS / f"{base}_{rare}.png"
        if f.exists():
            return f.as_uri()
    sys.exit(f"アイコンが無い：{c['name']}")


def at(entry, rare, lv):
    """表示の値：指定Lv以下で一番高いLvの値（無ければ0）"""
    best, val = -1, 0
    for k, v in ((entry or {}).get("表示") or {}).get(rare, {}).items():
        if best < int(k) <= lv:
            best, val = int(k), v
    return val


def vals(c, rare, lv):
    b = c["bonus"]
    return sum(at(b.get(k), rare, lv) for k in BASE), at(b.get("コツイベントボーナス"), rare, lv)


def rec_lv(c, top):
    for lv in (35, 37, 40, 45):
        if vals(c, "SR", lv) == top:
            return str(lv)
    for lv in (40, 42, 45, 50):
        if vals(c, "PSR", lv) == top:
            return "50" if lv == 50 else f"PSR{lv}"
    return "－"


def fmt(v):
    return str(int(v)) if float(v).is_integer() else str(v)


def name_html(n):
    m = re.match(r"\[(.*?)\](.*)", n)
    small, name = (m.group(1), m.group(2)) if m else ("", n)
    sm = f"<small>[{H.escape(small)}]</small>" if small else ""
    return f"{sm}<b>{H.escape(name)}</b>"


CSS = """
.tbl{position:absolute;left:60px;top:132px;width:1800px;background:#fff;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,.08);overflow:hidden;display:flex}
.band{flex:none;width:150px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:900;color:#14233a;font-size:84px;line-height:1}
.band small{font-size:40px;margin-top:10px}
table{flex:1;border-collapse:collapse;table-layout:fixed}
th{background:#33415c;color:#fff;font-weight:800;font-size:34px;height:58px;border-left:2px solid #5a6a88}
th.sub{font-size:28px;height:48px;background:#4a5a78}
th:first-child{border-left:0}
td{height:116px;border-top:2px solid #e3e6ea;border-left:2px solid #e3e6ea;text-align:center;font-weight:900;font-size:52px;white-space:nowrap}
td.nm{text-align:left;border-left:0;padding-left:20px}
td.nm div{display:flex;align-items:center;gap:22px}
td.nm img{width:96px;height:96px;border-radius:10px;flex:none}
td.nm p{display:flex;flex-direction:column;line-height:1.15}
td.nm small{font-size:26px;color:#666;font-weight:700;letter-spacing:-.5px}
td.nm b{font-size:44px;font-weight:900;letter-spacing:-.5px}
td.mx{background:#fff7d6}
td.l35{color:#33415c}
td.ev{font-size:48px}
"""


def page(rank, part, members):
    trs = ""
    for n in members:
        c = CHARS[n]
        top, low = vals(c, "PSR", 50), vals(c, "SR", 35)
        ev = (c.get("プロフィール") or {}).get("前後イベ") or "－"
        trs += (f'<tr><td class="nm"><div><img src="{icon(c)}"><p>{name_html(n)}</p></div></td>'
                f'<td class="ev">{H.escape(ev)}</td>'
                f'<td class="mx">{fmt(top[0])}</td><td class="l35">{fmt(low[0])}</td>'
                f'<td class="mx">{fmt(top[1])}</td><td class="l35">{fmt(low[1])}</td>'
                f'<td>{rec_lv(c, top)}</td></tr>')
    band = H.escape("高校" if rank == "高校キャラ" else rank) + (f"<small>{part}</small>" if part else "")
    head = ('<colgroup><col style="width:640px"><col style="width:130px"><col><col><col><col><col style="width:210px"></colgroup>'
            '<tr><th rowspan="2">キャラ</th><th rowspan="2">前後</th><th colspan="2">基礎合計</th><th colspan="2">コツボナ</th><th rowspan="2">推奨Lv</th></tr>'
            '<tr><th class="sub">PSR50</th><th class="sub">Lv35</th><th class="sub">PSR50</th><th class="sub">Lv35</th></tr>')
    sub = spec.get("subtitle", "")
    body = (f'<div class="title" style="top:4px;height:90px;line-height:90px;font-size:68px">{H.escape(spec["title"])}</div>'
            + (f'<div class="title" style="top:88px;height:40px;line-height:40px;font-size:30px;font-weight:700;color:#5a6577">{H.escape(sub)}</div>' if sub else "")
            + f'<div class="tbl"><div class="band" style="background:{COLOR.get(rank, "#ccc")}">{band}</div><table>{head}{trs}</table></div>')
    return (f'<!doctype html><html lang="ja"><head><meta charset="utf-8">{src["FONT"]}<style>{src["CSS"]}{CSS}</style></head>'
            f'<body>{body}<script>window.fit=()=>{{}}</script></body></html>')


for _, names in spec["rows"]:
    for n in names:
        assert n in CHARS, f"chars.json に無い名前：{n}"

DEST.mkdir(parents=True, exist_ok=True)
work = Path(tempfile.mkdtemp())
jobs, order, no = [], [], 0
RID = {"SS": "SS", "S": "S", "A": "A", "B": "B", "C": "C", "高校キャラ": "HS"}
for rank, names in spec["rows"]:
    k = math.ceil(len(names) / MAX)
    size = math.ceil(len(names) / k)
    for i in range(k):
        part = f"{'①②③④⑤'[i]}" if k > 1 else ""
        no += 1
        fn = f"{no:02d}_{RID.get(rank, 'X')}" + (f"_{i + 1}" if k > 1 else "") + ".png"
        h = work / f"{no}.html"
        h.write_text(page(rank, part, names[i * size:(i + 1) * size]))
        jobs.append([str(h), str(DEST / fn)])
        order.append(f"{fn}\t{rank}{part}\t" + "、".join(names[i * size:(i + 1) * size]))
(work / "jobs.json").write_text(json.dumps(jobs))
subprocess.run(["node", str(HERE / "shot.js"), str(work / "jobs.json")], check=True)
(DEST / "order.txt").write_text("\n".join(order) + "\n")
print("できあがり:", DEST)
