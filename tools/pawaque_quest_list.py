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
SOON = '<span class="qc-soon">配信後に追加します</span>'


def txt(s):
    return "<br>".join(e(x) for x in s.split("\n")) if s else SOON


out = ['<div class="qc-list">']
for q in D["クエスト"]:
    no, title = q["番号"], q["タイトル"]
    area = q["エリア数"]
    named = re.fullmatch(r"[①-⑳]", no) is not None
    head = f'{e(no)}{e(title)}' if named else (f'{e(no)}<span class="qc-sub">{e(title)}</span>' if title else e(no))
    rows = [("ドロップしやすいアイテム", txt(q["ドロップしやすいアイテム"])), ("ボスドロップ", txt(q["ボスドロップ"]))]
    imgs = "".join(f'<img class="qc-img" src="{{{{root}}}}img/{e(g["file"])}" alt="{e(g.get("説明") or no + "の画像")}" loading="lazy">'
                   + (f'<p class="qc-cap">{e(g["説明"])}</p>' if g.get("説明") else "") for g in q.get("画像", []))
    if q["管理人メモ"] or imgs:
        rows.append(("管理人メモ", (txt(q["管理人メモ"]) if q["管理人メモ"] else "") + imgs))
    if named and not title:
        head = f'{e(no)}<span class="qc-sub qc-soon">（配信後に追加）</span>'
    out.append(f'  <section class="qc" id="q{D["クエスト"].index(q) + 1}">')
    out.append(f'    <h3 class="qc-h"><span class="qc-t">{head}</span><span class="qc-a">エリア数<b>{area if area is not None else "－"}</b></span></h3>')
    out.append('    <dl class="qc-d">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>")
    out.append("  </section>")
out.append("</div>")
block = "\n".join(out)

s = page.read_text(encoding="utf-8")
assert "<!-- QUESTS:START -->" in s and "<!-- QUESTS:END -->" in s, "QUESTS の目印が見つからない"
s2 = re.sub(r"(<!-- QUESTS:START -->).*?(<!-- QUESTS:END -->)", lambda m: m.group(1) + "\n" + block + "\n  " + m.group(2), s, flags=re.S)
page.write_text(s2, encoding="utf-8")
print("ok", len(D["クエスト"]), "件")
