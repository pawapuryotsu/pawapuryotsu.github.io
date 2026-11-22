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


def item(x):
    # 「の契約書」は途中で折り返さない（幅320pxで「契約|書」と割れたため）
    t = e(x)
    if t.endswith("の契約書"):
        t = t[:-4] + '<span class="cp-nw">の契約書</span>'
    # ［○○］の二つ名が付いた契約書は青の太字（管理人 2026-11-16）
    return f'<span class="em-blue">{t}</span>' if x.startswith("［") and "契約書" in x else t


def lst(v):
    return "<br>".join(item(x) for x in v) if v else SOON


from datetime import datetime, timezone


def ended(t):
    # 「終了」（例 2026-11-26T14:00:00+09:00）を過ぎたか。ビルドした時点で過ぎていれば本体一覧に出さない
    return bool(t.get("終了")) and datetime.now(timezone.utc) >= datetime.fromisoformat(t["終了"])


def card(t, sid, lim, end=""):
    o = [f'  <section class="qc{" sz-lim" if lim else ""}" id="{sid}"{f' data-end="{e(end)}"' if end else ""}>']
    note = f'<span class="qc-a sz-note">※{e(t["期間"])}</span>' if t.get("期間") else ""
    o.append(f'    <h3 class="qc-h"><span class="qc-t">{e(t["対戦相手"])}</span>{note}</h3>')
    if t.get("画像"):
        o.append(f'    <div class="sz-b"><img class="qc-img sz-img" src="{{{{root}}}}img/{e(t["画像"])}" alt="{e(t["対戦相手"])}の神前試合" width="722" height="342" loading="lazy"></div>')
    rows = [("進化対象", lst(t.get("進化対象"))), ("固有スカウト選手候補", lst(t.get("固有スカウト選手候補")))]
    o.append('    <dl class="qc-d">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>")
    o.append("  </section>")
    return o


out = ['<div class="qc-list sz-list">']
# 並び順：期間限定（json の順）→ シナリオ番号順 → 番号なし（json の順）
ORDER = sorted(D["対戦相手"], key=lambda t: (0, 0) if t.get("期間") else ((1, t["シナリオ番号"]) if t.get("シナリオ番号") else (2, 0)))
# 「終了」がある学校（コラボなど）は、終了日時（日本時間14時）が来たら本体一覧から外し、
# ページ下部の「過去コラボの対戦相手まとめはコチラ」の中に移す（2026-11-22 管理人）。
# ビルド前でも外れるよう、ページ内スクリプトでも data-end を見て移す。
PAST = [t for t in ORDER if t.get("終了")]
for i, t in enumerate([t for t in ORDER if not ended(t)], 1):
    out += card(t, f"t{i}", bool(t.get("期間")), t.get("終了", ""))
out.append("</div>")
# 固有スカウト全員チーム加入時に得られる契約書（2026-11-16 管理人。分かったものから足す）
ALL = D.get("全員加入の契約書", [])
out.append("")
out.append('  <h2 id="all-join"><span class="cp-nw">固有スカウト</span><span class="cp-nw">全員チーム加入時に</span><span class="cp-nw">得られる契約書まとめ</span></h2>')
# 説明文（2026-11-19 管理人の文面）
out.append("  <p>固有スカウト候補選手全員を既にスカウト済みだったり、契約書+〇のスキルで固有スカウト候補よりも候補数の方が多くなる状態だと、どのチームにも属さない選手がスカウトに登場します。</p>")
out.append("  <p>狙い目となる主な契約書は以下の通りです。</p>")
out.append('  <ul class="sz-all">' + "".join(f"<li>{item(x)}</li>" for x in ALL) + "</ul>" if ALL else f"  <p>{SOON}</p>")
if PAST:
    out.append("")
    hid = "" if any(ended(t) for t in PAST) else " hidden"
    out.append(f'  <details class="rs-old sz-past" id="past"{hid}>')
    out.append("  <summary>過去コラボの対戦相手まとめはコチラ</summary>")
    out.append('  <div class="rs-old-in qc-list sz-list">')
    for i, t in enumerate(PAST, 1):
        o = card(t, f"p{i}", False)
        o[0] = o[0].replace("<section ", f'<section{"" if ended(t) else " hidden"} data-start="{e(t["終了"])}" ', 1)
        out += o
    out.append("  </div>")
    out.append("  </details>")
    # 終了日時を過ぎたら：本体一覧から消して、過去コラボの中に出す（ボタンは1校でも入ったら出す）
    out.append("  <script>(function(){var n=Date.now();document.querySelectorAll('.sz-list section[data-end]').forEach(function(e){if(n>=Date.parse(e.getAttribute('data-end')))e.parentNode.removeChild(e)});"
               "var b=document.getElementById('past');if(!b)return;b.querySelectorAll('section[data-start]').forEach(function(e){if(n>=Date.parse(e.getAttribute('data-start'))){e.hidden=false;b.hidden=false}})})();</script>")
block = "\n".join(out)
s = page.read_text(encoding="utf-8")
assert "<!-- SHINZEN:START -->" in s and "<!-- SHINZEN:END -->" in s, "SHINZEN の目印が見つからない"
s = re.sub(r"(<!-- SHINZEN:START -->).*?(<!-- SHINZEN:END -->)", lambda m: m.group(1) + "\n" + block + "\n  " + m.group(2), s, flags=re.S)
page.write_text(s, encoding="utf-8")
print("ok", len(D["対戦相手"]), "件")

import subprocess, sys
subprocess.run([sys.executable, str(here / "tools/pawaque_saikyuki_top.py")], check=True)
