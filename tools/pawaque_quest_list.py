"""パワクエ西球記のクエスト一覧ページ（src/pages/pawaque-saikyuki-quest.html）の「クエスト一覧」を作る。
データは src/pawaque_data/saikyuki_quests.json（管理人が送ったゲーム画面のとおりに入れる。推測で入れない）。
使い方： python3 tools/pawaque_quest_list.py → python3 build.py
ページの <!-- QUESTS:START --> と <!-- QUESTS:END --> の間を書き換える。"""
import html, json, re
from pathlib import Path

here = Path(__file__).resolve().parent.parent
D = json.loads((here / "src/pawaque_data/saikyuki_quests.json").read_text(encoding="utf-8"))
page = here / "src/pages/pawaque-saikyuki-quest.html"
e = html.escape
SOON = '<span class="qc-soon">あとで追加します</span>'


def emtxt(s):
    # 赤メモ・青メモ：「|」で区切ると、その区切りでだけ改行する（言葉の途中で切れないように）
    return "<br>".join("".join(f'<span class="cp-nw">{e(p)}</span>' for p in x.split("|")) if "|" in x else e(x) for x in s.split("\n"))


def item(x):
    # ［○○］の二つ名が付いた契約書は青の太字（管理人 2026-11-16）
    return f'<span class="em-blue">{e(x)}</span>' if x.startswith("［") and "契約書" in x else e(x)


def marks(s):
    # 管理人メモの {青:…}＝青文字・{青太:…}＝青太字・{赤:…}＝赤文字（2026-11-17 管理人）
    for tag, cls in (("青太", "em-blue"), ("青", "tx-b"), ("赤太", "em-red"), ("赤", "tx-r")):
        s = re.sub(r"\{" + tag + r":(.*?)\}", lambda m: f'<span class="{cls}">{m.group(1)}</span>', s)
    return s


def txt(s):
    return "<br>".join(marks(item(x)) for x in s.split("\n")) if s else SOON


out = ['<div class="qc-list">']
for q in D["クエスト"]:
    no, title = q["番号"], q["タイトル"]
    area = q["エリア数"]
    named = re.fullmatch(r"[①-⑳]", no) is not None
    # タイトルも「|」で区切ると、その区切りでだけ改行する（スマホで言葉の途中で切れないように）
    head = f'{e(no)}{emtxt(title)}' if named else (f'{e(no)}<span class="qc-sub">{emtxt(title)}</span>' if title else e(no))
    rows = [("ドロップしやすいアイテム", txt(q["ドロップしやすいアイテム"])), ("ボスドロップ", txt(q["ボスドロップ"]))]
    imgs = "".join(f'<img class="qc-img" src="{{{{root}}}}img/{e(g["file"])}" alt="{e(g.get("説明") or no + "の画像")}" loading="lazy">'
                   + (f'<p class="qc-cap">{e(g["説明"])}</p>' if g.get("説明") else "") for g in q.get("画像", []))
    red = f'<span class="em-red">{emtxt(q["赤メモ"])}</span>' if q.get("赤メモ") else ""
    blue = f'<span class="em-blue">{emtxt(q["青メモ"])}</span>' if q.get("青メモ") else ""
    memo = "<br>".join(x for x in (blue, red, txt(q["管理人メモ"]) if q["管理人メモ"] else "") if x)
    if memo or imgs:
        rows.append(("管理人メモ", memo + imgs))
    if named and not title:
        head = f'{e(no)}<span class="qc-sub qc-soon">（あとで追加）</span>'
    # 名前の横の印（2026-11-17 管理人）：祈願エンディングあり→※祈願あり、仙術は使用不可→赤の※仙術不可、④⑪→※周回オススメ!
    tags = []
    if q.get("周回オススメ"):
        tags.append('<span class="qc-tag qc-tag-b">※周回オススメ!</span>')
    if "祈願エンディングあり" in q.get("青メモ", ""):
        tags.append('<span class="qc-tag qc-tag-b">※祈願あり</span>')
    if "仙術は使用不可" in q.get("赤メモ", ""):
        tags.append('<span class="qc-tag qc-tag-r">※仙術不可</span>')
    tag = f'<span class="qc-tags">{"".join(tags)}</span>' if tags else ""
    # タップで詳細を開く（details）。#q4 などのリンクで来たら開く（ページ下のスクリプト）
    out.append(f'  <details class="qc qc-x" id="q{D["クエスト"].index(q) + 1}">')
    out.append(f'    <summary><h3 class="qc-h"><span class="qc-t"><span class="qc-n">{head}</span>{tag}</span><span class="qc-a">エリア数<b>{area if area is not None else "－"}</b></span><span class="qc-arw" aria-hidden="true"></span></h3></summary>')
    out.append('    <dl class="qc-d">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>")
    # 攻略ページがあるクエストは、開いた中の最後に「詳しい攻略はコチラ」リンク（2026-11-18 管理人、むずクエ）
    if q.get("攻略ページ"):
        out.append(f'    <p class="qc-more"><a href="{{{{root}}}}{e(q["攻略ページ"])}">詳しい攻略はコチラ</a></p>')
    out.append("  </details>")
out.append("</div>")
out.append('<script>(()=>{const o=()=>{const d=location.hash&&document.getElementById(location.hash.slice(1));if(d&&d.tagName==="DETAILS"){d.open=true;d.scrollIntoView()}};o();addEventListener("hashchange",o)})();</script>')
block = "\n".join(out)

s = page.read_text(encoding="utf-8")
assert "<!-- QUESTS:START -->" in s and "<!-- QUESTS:END -->" in s, "QUESTS の目印が見つからない"
s2 = re.sub(r"(<!-- QUESTS:START -->).*?(<!-- QUESTS:END -->)", lambda m: m.group(1) + "\n" + block + "\n  " + m.group(2), s, flags=re.S)
page.write_text(s2, encoding="utf-8")
print("ok", len(D["クエスト"]), "件")

import subprocess, sys
subprocess.run([sys.executable, str(here / "tools/pawaque_saikyuki_top.py")], check=True)
