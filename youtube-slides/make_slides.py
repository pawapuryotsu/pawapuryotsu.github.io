"""YouTube動画用のランキングスライド（1920×1080 PNG）を作る。

データはサイトから取り出す（推測で値を入れない）：
  - Tier表・アイコン・目印 … docs/ranking/<キー>/index.html（先に build.py でサイトを作っておく）
  - 重要ボーナス・アイテム追加枠 … charpages.py と同じ計算（ページのあるキャラはページの表と一致するか確認する）
使い方は youtube-slides/README.md
"""
import json, re, subprocess, sys, shutil, tempfile, zipfile, html as H
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
KEY = sys.argv[1] if len(sys.argv) > 1 else "roman"
DEST = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "out"
WORK = Path(tempfile.mkdtemp())

rank = json.load(open(SITE / "src/ranking/ranking.json"))["ranking"][KEY]
# スライドの重要ボーナスから外す項目（ランキングの「種別」ごと。キャラページには両方の学園用が出るが、動画では不要：管理人指示 2026-11-10）
#   投手（ロマン開花學園）…アンドロメダ用のコツイベントボーナス・試合経験点ボーナスを外す
#   野手（アンドロメダ学園）…ロマン用の練習効果アップ・スペシャルタッグボーナスを外す
HIDE = {"投手": ["コツイベントボーナス", "試合経験点ボーナス"],
        "野手": ["練習効果アップ", "スペシャルタッグボーナス"]}.get(rank.get("種別"), [])
TITLE = rank["title"]
page = (SITE / f"docs/ranking/{KEY}/index.html").read_text()
table = page[page.find('<div class="tier-table">'):]

# Tier表：行ごとに (ランク, [キャラ]) を取り出す
rows = []
for part in table.split('<div class="tier-row">')[1:]:
    t, body = re.match(r'<div class="tier tier-(\w+)">\w+</div><div class="tier-ic">(.*)', part, re.S).groups()
    chars = []
    for m in re.finditer(r'<(?:a|div) class="rk-ic"(?: href="../../chars/(\d+)/")?>(.*?)</(?:a|div)>', body, re.S):
        pid, inner = m.group(1), m.group(2)
        img = re.search(r'src="../../img/chars/([^"]+)"', inner)
        small = re.search(r"<small>(.*?)</small>", inner)
        segs = re.findall(r"<b>(.*?)</b>", inner)
        name = "".join(segs)
        marks = re.findall(r'<em class="(rk-\w+)">(.*?)</em>', inner)
        chars.append(dict(pid=pid, img=(SITE / "docs/img/chars" / img.group(1)).as_uri() if img else None,
                          small=small.group(1) if small else "", name=name, segs=segs, marks=marks,
                          full=(small.group(1) if small else "") + name))
    rows.append((t, chars))

# ranking.json の並びと突き合わせ（取り出しミス防止）
for t, chars in rows:
    want = [x["name"] for x in rank["ランク"].get(t, [])]
    got = [H.unescape(c["full"]) for c in chars]
    assert want == got, (t, want, got)

# 1行の最大人数に合わせてアイコンの大きさを決める（折り返さない）
MAXN = max(len(c) for _, c in rows)
FW = min(151, (1720 - 138 - 20) // MAXN)
CW = min(115, (1158 - 104 - 20) // MAXN)

FONT = '<link href="https://fonts.googleapis.com/css2?family=M+PLUS+1p:wght@500;700;800;900&family=Zen+Kaku+Gothic+New:wght@700;900&display=swap" rel="stylesheet">'
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1920px;height:1080px;overflow:hidden;background:#eaeeea;font-family:'M PLUS 1p',sans-serif;color:#14233a}
.title{position:absolute;left:0;right:0;top:8px;height:100px;text-align:center;font-weight:900;font-size:76px;line-height:100px;letter-spacing:2px;color:#14233a}
.tt{position:absolute;background:#fff;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,.08);overflow:hidden;display:flex;flex-direction:column}
.row{display:flex;flex:1;border-top:2px solid #e3e6ea;min-height:0}
.row:first-child{border-top:0}
.tier{flex:none;display:flex;align-items:center;justify-content:center;font-weight:900;color:#14233a}
.tier-SS{background:#ff6b6b}.tier-S{background:#ffa94d}.tier-A{background:#ffe066}.tier-B{background:#a9e34b}
.ics{flex:1;display:flex;align-items:flex-start;padding:var(--pad) 10px 0}
.ic{position:relative;display:flex;flex-direction:column;align-items:center;width:var(--w);text-align:center;line-height:1.25;font-weight:700}
.ic img,.noimg{width:var(--icon);height:var(--icon);border-radius:10px;display:block;background:#f3e7c2}
.ic small{display:block;font-size:var(--sm);color:#666;white-space:nowrap;margin-top:6px;letter-spacing:-.5px;font-weight:500}
.ic span{display:block;font-size:var(--nm);white-space:nowrap;letter-spacing:-.5px}
.ic span b{font-weight:inherit;display:inline-block}
.ic span.ln{white-space:normal;font-size:calc(var(--nm)*.82)}
.ic img+span{margin-top:6px}
.ic em{font-style:normal;font-weight:800;font-size:var(--sm);white-space:nowrap;letter-spacing:-.5px}
.rk-school{color:#1565c0}.rk-supreme{color:#c62828}
.ic.sel::after{content:"";position:absolute;left:-7px;right:-7px;top:-8px;bottom:-10px;border:7px solid #e8000b;border-radius:4px}
.panel{position:absolute;left:1188px;top:118px;width:712px;height:740px;background:#fff;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,.08);padding:26px 34px;overflow:hidden}
.panel h2{font-weight:900;font-size:46px;line-height:1.2;padding-left:22px;border-left:12px solid #2e7d32;margin-bottom:18px;white-space:nowrap}
.panel table{width:100%;border-collapse:collapse}
.panel th{text-align:left;font-weight:800;font-size:31px;color:#33415c;padding:14px 10px 14px 0;vertical-align:top;white-space:nowrap;width:1%}
.panel td{font-weight:900;font-size:40px;padding:10px 0 10px 18px;vertical-align:top;line-height:1.25}
.panel tr{border-top:2px solid #e3e6ea}
.panel tr:first-child{border-top:0}
.panel td .awk{white-space:nowrap;font-size:.62em;font-weight:800;color:#555;margin-left:4px}
.panel td .step{display:block;white-space:nowrap;color:#d62828;font-size:.88em}
.panel td .step small{font-size:.62em;font-weight:800;margin-left:2px}
.panel td{white-space:nowrap}
"""
FIT_JS = """
<script>
window.fit=()=>{
  // ボーナス欄：はみ出すなら全体を小さくする
  const pn=document.querySelector('.panel');
  if(pn){const h=pn.querySelector('h2');let s=46;while(h.scrollWidth>h.clientWidth&&s>26){s-=2;h.style.fontSize=s+'px'}
    let z=1;while((pn.scrollHeight>pn.clientHeight+1||pn.scrollWidth>pn.clientWidth+1)&&z>0.5){z-=0.03;pn.querySelector('table').style.zoom=z}}
};
</script>"""


def e(s):
    return H.escape(H.unescape(s))


def tier_html(sel=None, *, left, top, width, height, icon, w, tiercol, tierfont, nm, sm, pad):
    out = [f'<div class="tt" style="left:{left}px;top:{top}px;width:{width}px;height:{height}px;'
           f'--icon:{icon}px;--w:{w}px;--nm:{nm}px;--sm:{sm}px;--pad:{pad}px">']
    for t, chars in rows:
        ics = ""
        for c in chars:
            img = f'<img src="{c["img"]}">' if c["img"] else '<span class="noimg"></span>'
            small = f"<small>{c['small']}</small>" if c["small"] else ""
            marks = "".join(f'<em class="{k}">{v}</em>' for k, v in c["marks"])
            cls = "ic sel" if c is sel else "ic"
            nm = "".join("<b>" + x + "</b>" for x in c["segs"])
            ln = ' class="ln"' if len(c["segs"]) > 1 or len(H.unescape(c["name"])) > 8 else ""
            ics += f'<div class="{cls}">{img}{small}<span{ln}>{nm}</span>{marks}</div>'
        out.append(f'<div class="row"><div class="tier tier-{t}" style="width:{tiercol}px;font-size:{tierfont}px">{t}</div><div class="ics">{ics}</div></div>')
    out.append("</div>")
    return "".join(out)


def doc(body):
    return f'<!doctype html><html lang="ja"><head><meta charset="utf-8">{FONT}<style>{CSS}</style></head><body>{body}{FIT_JS}</body></html>'


sys.path.insert(0, str(SITE))
import charpages
CONFIG = json.load(open(SITE / "src/chars/config.json"))
CHARS = {c["name"]: c for c in json.load(open(SITE.parent / "pawa-data/event-chars/chars.json"))}


def bonus_rows(full):
    """サイトのキャラページ（charpages.build_page）と同じ計算で、重要ボーナスの表とアイテム追加枠を作る"""
    c = CHARS[full]
    bonus = c["bonus"]
    ctype = charpages.char_type(c, CONFIG["種別の判定"])
    important = [(n, bonus[n]) for n in CONFIG["重要ボーナス"][ctype]
                 if n in bonus and (charpages.bonus_lines(bonus[n]) or bonus[n].get("固有文字"))]
    # 一番下に 追加枠／キャラ持参アイテム（キャラページと同じ）
    item_rows = "".join(f'<tr><th>{charpages.e(it.get("種類") or "アイテム")}</th><td><b>{charpages.e(it["名前"])}</b></td></tr>'
                        for it in c.get("アイテム") or [] if it.get("名前"))
    tb = charpages.bonus_table(important, item_rows)
    return re.search(r"<tbody>(.*)</tbody>", tb, re.S).group(1)


def page_rows(pid):
    """確認用：作成済みのキャラページから取り出した表"""
    p = (SITE / f"docs/chars/{pid}/index.html").read_text()
    i = p.find("の重要ボーナス</span></h2>")
    return re.search(r'<table class="cp-bonus"><tbody>(.*?)</tbody></table>', p[i:], re.S).group(1)


def char_slide(c):
    base = c["name"]
    body = f'<div class="title">{e(TITLE)}</div>'
    body += tier_html(c, left=8, top=118, width=1158, height=740, icon=min(94, CW - 14), w=CW, tiercol=104, tierfont=50, nm=round(19 * min(1, CW / 115), 1), sm=round(14 * min(1, CW / 115), 1), pad=12)
    rows_html = "".join(r for r in re.findall(r"<tr>.*?</tr>", bonus_rows(H.unescape(c["full"])), re.S)
                        if re.match(r"<tr><th>(.*?)</th>", r).group(1) not in HIDE)
    body += f'<div class="panel"><h2>{base}の重要ボーナス</h2><table>{rows_html}</table></div>'
    return doc(body)


# 画面下は動画編集で文字を乗せるために空けておく（帯の文章はClaudeが作らない：管理人指示 2026-11-10）
# ファイル名は文字化けしないように英数字だけ（番号はTier表の左上から右下への順）
OUT = DEST / f"{KEY}_notext"
OUT.mkdir(parents=True, exist_ok=True)
jobs = []
for f in OUT.glob("*.png"):
    f.unlink()
full = doc(f'<div class="title">{e(TITLE)}</div>' +
           tier_html(left=100, top=108, width=1720, height=962, icon=min(128, FW - 20), w=FW, tiercol=138, tierfont=72, nm=round(26 * min(1, FW / 151), 1), sm=round(18 * min(1, FW / 151), 1), pad=18))
(WORK / "00.html").write_text(full)
jobs.append([str(WORK / "00.html"), str(OUT / "00_tier.png")])
n = 0
order = []
for t, chars in rows:
    for c in chars:
        n += 1
        if c["pid"]:
            assert page_rows(c["pid"]) == bonus_rows(H.unescape(c["full"])), c["full"]
        fn = WORK / f"{n:02d}.html"
        fn.write_text(char_slide(c))
        jobs.append([str(fn), str(OUT / f"{n:02d}_{t}.png")])
        order.append(f"{n:02d}_{t}.png  {H.unescape(c['full'])}")

(WORK / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False))
subprocess.run(["node", str(HERE / "shot.js"), str(WORK / "jobs.json")], check=True)
(OUT / "order.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
with zipfile.ZipFile(DEST / f"{KEY}_slides.zip", "w") as z:
    for f in sorted(OUT.glob("*.png")):
        z.write(f, f.name)
shutil.rmtree(WORK)
print("\n".join(order))
print(f"できあがり: {OUT}（{len(jobs)}枚）と {DEST / (KEY + '_slides.zip')}")
