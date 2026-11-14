"""パワクエのミッション報酬まとめページ（src/pages/pawaque-mission.html）を作る。
データは src/pawaque_data/mission.json（ストーリーごとのミッション一覧。管理人が送った公式ミッション一覧を読み取ったもの）。
使い方： python3 tools/pawaque_mission_page.py → python3 build.py
新しいストーリーが増えたら mission.json に1つ足して、もう一度これを動かす。"""
import html, json, re
from collections import Counter, OrderedDict
from pathlib import Path

here = Path(__file__).resolve().parent.parent
D = json.loads((here / "src/pawaque_data/mission.json").read_text(encoding="utf-8"))
AS_OF = "2026/11/14"
e = html.escape
CATS = ["クエストクリア", "プレイ回数", "ベストチームのランク", "チーム総合力の累計", "チームの能力", "スカウト人数", "ボス戦の勝利数", "その他"]


def qkey(cond):
    m = re.match(r"クエスト(\d+)をクリア", cond)
    return int(m.group(1)) if m else {"むずクエをクリア": 21, "むちゃクエをクリア": 22, "むりクエをクリア": 23}.get(cond, 99)


def items(rows):
    c = Counter()
    for r in rows:
        for it in r["報酬"].split("、"):
            m = re.match(r"(.+)×(\d+)$", it)
            c[m.group(1) if m else it] += int(m.group(2)) if m else 1
    return c


BREAKS = {"冥界トライアル": ["冥界", "トライアル"], "幻想野球冒険伝": ["幻想野球", "冒険伝"]}
SHORT = {"冥界トライアル": "冥界", "幻想野球冒険伝": "幻想"}   # 合計の表の見出しは、スマホでは短い名前にする


def spans(parts):
    parts = [x for x in parts if x]
    return "".join(f'<span class="pm-nb">{e(x)}</span>' for x in parts) if len(parts) > 1 else e("".join(parts))


def nb(name):
    """長い名前は、意味の切れ目でだけ折り返す"""
    return spans(BREAKS.get(name) or re.split(r"(?=博士像|のパワター|の極意)|(?<=%)(?=ガチャ券)", name))


def nbc(cond):
    """条件の文は「〜が」「〜で」「〜を」「〜に」の後ろでだけ折り返す"""
    if cond.startswith("チーム総合力の累計が"):
        return spans(["チーム総合力の", cond[len("チーム総合力の"):]])
    return spans(re.split(r"(?<=[がでをに])(?=.{3,}$)|(?<=以上)(?=スカウト)", cond))


def rew_item(x, comma, only):
    """報酬1つ分。2つ以上並ぶときは、報酬と報酬の間でだけ折り返す"""
    parts = [p for p in re.split(r"(?=博士像|のパワター|の極意)|(?<=%)(?=ガチャ券)", x) if p]
    if comma:
        parts[-1] += "、"
    body = "".join(f'<span class="pm-nb">{e(p)}</span>' for p in parts)
    return f'<span class="em-blue">{body}</span>' if re.sub(r"×\d+$", "", x) in only else body


def head(name):
    return f'<span class="pm-full">{nb(name)}</span><span class="pm-abbr">{e(SHORT[name])}</span>' if name in SHORT else e(name)


def num(s):
    return re.sub(r"\d{5,}", lambda m: f"{int(m.group()):,}", s)


stories = []
for d in D:
    rows = d["ミッション"]
    by = OrderedDict((c, [r for r in rows if r["区分"] == c]) for c in CATS)
    by["クエストクリア"].sort(key=lambda r: (qkey(r["条件"]), r["コスト"] is None))   # 追加の報酬の行は、同じクエストのすぐ下に
    stories.append(dict(name=d["ストーリー"], rows=rows, by=by, cost=sum(r["コスト"] or 0 for r in rows), items=items(rows)))

common = set.intersection(*(set(s["items"]) for s in stories))
for s in stories:
    s["only"] = [k for k in s["items"] if k not in common]

out = []
out.append(f"""<!--
title: パワクエ ミッション報酬まとめ｜パワプロアプリ攻略ベース
description: パワプロアプリのパワクエのミッション報酬を、球炎島・月姫伝・冥界トライアル・幻想野球冒険伝のストーリーごとに一覧にまとめました。アイテムコストの合計と、ストーリーごとの違いも比べられます。
path: pawaque/mission/
nav: pawaque
crumb: ミッション報酬まとめ
noindex: yes
-->
<section class="phead"><p class="eyebrow">パワクエ</p><h1><span class="mk"><i>ミッション報酬まとめ</i></span></h1><p>パワクエのミッションでもらえる報酬を、ストーリーごとに一覧にしました。</p></section>
<div class="prose">
  <nav class="toc" aria-label="このページの目次">
  <b>もくじ</b>
  <ol>
    <li><a href="#compare">ストーリーごとの違い</a></li>
    <li><a href="#total">もらえる報酬の合計</a></li>
    <li><a href="#list">ミッション一覧</a></li>
  </ol>
  </nav>
  <p>ミッションをクリアすると、報酬のほかに<span class="em-blue">アイテムコストの上限が増えます。</span>アイテムコストが増えるほど、強いアイテムをたくさん持ち込めるように<span class="cp-nw">なります。</span></p>
  <p class="pm-note">{AS_OF} 時点の内容です。</p>

  <h2 id="compare">ストーリーごとの違い</h2>
  <div class="bt-wrap pm-w"><table class="bt pm-t pm-cmp">
    <thead><tr><th scope="col">ストーリー</th><th scope="col">件数</th><th scope="col"><span class="pm-nb">コスト</span><span class="pm-nb">合計</span></th><th scope="col"><span class="pm-nb">このストーリー</span><span class="pm-nb">だけの報酬</span></th></tr></thead>
    <tbody>""")
for s in stories:
    only = "<br>".join(nb(k) for k in s["only"]) or "なし"
    out.append(f'      <tr><th scope="row">{nb(s["name"])}</th><td>{len(s["rows"])}</td><td>+{s["cost"]}</td><td class="pm-l">{only}</td></tr>')
out.append("""    </tbody>
  </table></div>

  <h2 id="total">もらえる報酬の合計</h2>
  <p>ミッションを全部クリアしたときにもらえる数です。</p>
  <div class="bt-wrap pm-w"><table class="bt pm-t pm-sum">
    <thead><tr><th scope="col">報酬</th>""" + "".join(f'<th scope="col">{head(s["name"])}</th>' for s in stories) + "</tr></thead>\n    <tbody>")
order = []
for s in stories:
    for k in s["items"]:
        if k not in order:
            order.append(k)
order = [k for k in order if k in common] + [k for k in order if k not in common]
for k in order:
    vals = [s["items"].get(k, 0) for s in stories]
    diff = len(set(vals)) > 1
    out.append(f'      <tr><th scope="row">{nb(k)}</th>' + "".join(f'<td{" class=pm-df" if diff and v == max(vals) else ""}>{v if v else "－"}</td>' for v in vals) + "</tr>")
out.append("""    </tbody>
  </table></div>
  <p class="pm-note">ストーリーで数が違う報酬は、多い方に色を付けています。<span class="pm-abbr">「冥界」は冥界トライアル、「幻想」は幻想野球冒険伝です。</span></p>

  <h2 id="list">ミッション一覧</h2>
  <p>ストーリーを選ぶと、そのストーリーのミッションが表示されます。</p>
  <div class="pm-tabs" role="group" aria-label="ストーリーを選ぶ">""" + "".join(f'<button type="button" data-pm="{i}"{" class=on" if i == 0 else ""}>{e(s["name"])}</button>' for i, s in enumerate(stories)) + "</div>")
for i, s in enumerate(stories):
    out.append(f'  <section class="pm-story" data-pm="{i}">\n  <h3 class="pm-h">{e(s["name"])}編（{len(s["rows"])}件・アイテムコスト +{s["cost"]}）</h3>')
    for c, rows in s["by"].items():
        if not rows:
            continue
        out.append(f'  <h4 class="pm-c">{e(c)}</h4>\n  <div class="bt-wrap pm-w"><table class="bt pm-t pm-m">\n    <thead><tr><th scope="col">条件</th><th scope="col">コスト</th><th scope="col">報酬</th></tr></thead>\n    <tbody>')
        for r in rows:
            rew = "".join(rew_item(x, i < n - 1, s["only"]) for n in [len(r["報酬"].split("、"))] for i, x in enumerate(r["報酬"].split("、")))
            cost = f'+{r["コスト"]}' if r["コスト"] else "－"
            out.append(f'      <tr><th scope="row">{nbc(num(r["条件"]))}</th><td>{cost}</td><td class="pm-l">{rew}</td></tr>')
        out.append("    </tbody>\n  </table></div>")
    out.append("  </section>")
out.append("""  <script>(()=>{const b=[...document.querySelectorAll(".pm-tabs button")],s=[...document.querySelectorAll(".pm-story")];
const show=i=>{b.forEach(x=>x.classList.toggle("on",x.dataset.pm==i));s.forEach(x=>x.hidden=x.dataset.pm!=i)};
b.forEach(x=>x.addEventListener("click",()=>show(x.dataset.pm)));show(0)})()</script>
</div>
""")
(here / "src/pages/pawaque-mission.html").write_text("\n".join(out), encoding="utf-8")
print("src/pages/pawaque-mission.html を作りました:", [(s["name"], len(s["rows"]), s["cost"], s["only"]) for s in stories])
