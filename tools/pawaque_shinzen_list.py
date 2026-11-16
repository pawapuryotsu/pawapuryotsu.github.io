"""パワクエ西球記の神前試合まとめページ（src/pages/pawaque-saikyuki-shinzen.html）の「対戦相手一覧」を作る。
データは src/pawaque_data/saikyuki_shinzen.json（管理人が送ったゲーム画面のとおりに入れる。推測で入れない）。
使い方： python3 tools/pawaque_shinzen_list.py → python3 build.py
ページの <!-- SHINZEN:START --> と <!-- SHINZEN:END --> の間を書き換える。"""
import html, json, re
from pathlib import Path

here = Path(__file__).resolve().parent.parent
D = json.loads((here / "src/pawaque_data/saikyuki_shinzen.json").read_text(encoding="utf-8"))
page = here / "src/pages/pawaque-saikyuki-shinzen.html"
e = html.escape
SOON = '<span class="qc-soon">あとで追加します</span>'


def lst(v):
    return "<br>".join(e(x) for x in v) if v else SOON


out = ['<div class="qc-list sz-list">']
for i, t in enumerate(D["対戦相手"], 1):
    out.append(f'  <section class="qc" id="t{i}">')
    out.append(f'    <h3 class="qc-h"><span class="qc-t">{e(t["対戦相手"])}</span></h3>')
    body = ""
    if t.get("画像"):
        body += f'<img class="qc-img sz-img" src="{{{{root}}}}img/{e(t["画像"])}" alt="{e(t["対戦相手"])}の神前試合" width="722" height="342" loading="lazy">'
    rows = [("進化対象", lst(t.get("進化対象"))), ("固有スカウト選手候補", lst(t.get("固有スカウト選手候補")))]
    if body:
        out.append(f'    <div class="sz-b">{body}</div>')
    out.append('    <dl class="qc-d">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>")
    out.append("  </section>")
out.append("</div>")
block = "\n".join(out)
s = page.read_text(encoding="utf-8")
assert "<!-- SHINZEN:START -->" in s and "<!-- SHINZEN:END -->" in s, "SHINZEN の目印が見つからない"
s = re.sub(r"(<!-- SHINZEN:START -->).*?(<!-- SHINZEN:END -->)", lambda m: m.group(1) + "\n" + block + "\n  " + m.group(2), s, flags=re.S)
page.write_text(s, encoding="utf-8")
print("ok", len(D["対戦相手"]), "件")
