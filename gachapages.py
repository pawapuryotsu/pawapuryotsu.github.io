# ガチャ記事（/gacha/<id>/）を src/gacha/<id>.json から作る。build.py から呼ばれる。
# 新しいガチャを足すとき：src/gacha/<id>.json を作る → python3 gacha_calc/build_tables.py → python3 build.py
# id は「開始日_キャラ」（例 2026_1111_shampoo）。URLに「-」は使わない。
import html as _h, json
import charpages   # ランキングでの評価・文字の色指定を、キャラページと同じ形で出すため（build.py で charpages.generate() の後に呼ぶ）
from pathlib import Path

e = _h.escape
RS = ["PSR", "SR", "PR", "R"]


def _pct(v):
    return f"{v:g}%"


def _steps_table(g):
    rows = []
    for i, s in enumerate(g["steps"]):
        fixed = "<br>".join(e(x["label"]) for x in s["slots"] if x["n"] == 1 and x["label"] != "上記以外") or "なし"
        rows.append(f'<tr class="g-s{i % 4 + 1}"><td>{e(s["name"])}</td><td>{s["pulls"]}連</td><td>{s["cost"]}個</td><td class="g-l">{fixed}</td></tr>')
    return ('<div class="bt-wrap"><table class="bt g-t"><thead><tr><th scope="col">ステップ</th><th scope="col">連数</th>'
            '<th scope="col">石</th><th scope="col">確定枠</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def _rate_table(g):
    rows = []
    for i, s in enumerate(g["steps"]):
        for x in s["slots"]:
            cells = "".join(f'<td>{_pct(x["rarity"][r]) if r in x["rarity"] else "—"}</td>' for r in RS)
            kind = "確定枠" if x["label"] != "上記以外" else "通常枠"
            who = f'<wbr><span class="cp-nw">（{e(g["chara"])}のみ）</span>' if x["target"] == "only" else ""
            rows.append(f'<tr class="g-s{i % 4 + 1}"><td class="g-l">{e(s["name"])}<br><small><span class="cp-nw">{kind}{x["n"]}枚</span>{who}</small></td>{cells}</tr>')
    share = "・".join(f'<span class="cp-nw">{r} {_pct(g["share"][r])}</span>' for r in RS if r in g["share"])
    return ('<div class="bt-wrap"><table class="bt g-t"><thead><tr><th scope="col">枠</th>' + "".join(f'<th scope="col">{r}</th>' for r in RS)
            + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            + f'<p>{e(g["chara"])}のみの枠以外で、そのレアリティが出たときに{e(g["chara"])}になる割合：{share}</p>')


def _eval_html(g, src_dir):
    """「管理人の評価」。comment＝管理人の考え（文字の色指定 {太:…} などはキャラページと同じ）、
    イベキャラの評価（ランキングでの位置づけ・キャラページの評価文）があれば一緒に出す"""
    com = g.get("comment") or []
    if isinstance(com, str):
        com = [com] if com else []
    name = g["chara"]
    tf = src_dir / "chars" / "texts" / f"{name}.json"
    text = json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else {}
    chara_eval = charpages.ranking_eval_html(name, "{{root}}") + charpages.paras(text.get("評価", []))
    if not com and not chara_eval:
        return ""
    out = '<h2 id="eval">管理人の評価</h2>' + charpages.paras(com)
    if com and g.get("comment_date"):
        out += f'<p class="cp-evdate"><span class="rk-date">【記入日{e(g["comment_date"])}】</span></p>'
    if chara_eval:
        out += (f'<h3>イベキャラとしての評価</h3>{chara_eval}'
                f'<p><a href="{{{{root}}}}{e(g["char_page"])}">{e(name)}の<span class="cp-nw">ページを見る</span></a></p>')
    return out


def _body(g, root_icon, src_dir):
    c = e(g["chara"])
    data = {k: g[k] for k in ("id", "chara", "loop", "share", "steps")}
    data["tables"] = g["tables"]
    loop_note = (f'1周＝{"〜".join([g["steps"][0]["name"], g["steps"][-1]["name"]])}'
                 f'（{sum(s["pulls"] for s in g["steps"])}連・パワストーン{sum(s["cost"] for s in g["steps"])}個）。') if g.get("loop") else ""
    comment = _eval_html(g, src_dir)
    kmax = g["tables"]["K"]
    dj = "".join(f'<label><span class="g-{r}">{r}像</span><select data-dj="{r}" autocomplete="off" aria-label="{r}ダイジョーブ博士像の枚数">'
                 + "".join(f'<option value="{i}">{i}枚</option>' for i in range(kmax + 1)) + "</select></label>" for r in RS)
    # g["sources"]（公式ページのURL）は記録用。ゲーム内のページなので記事にはリンクを載せない（2026-11-12 管理人）
    return f'''<section class="phead"><p class="eyebrow">ガチャ</p><h1><span class="mk"><i>{c}のガチャは</i> <i>引くべき？</i></span></h1><p>{e(g["title"])}で、{c}のSR Lv45・PSR Lv50を作るのに何周必要かを<span class="cp-nw">計算しました。</span>引くべきか迷っている人は、下の確率と<span class="cp-nw">石の数を目安にしてください。</span></p></section>
<div class="prose">
  <p class="g-meta"><img src="{{{{root}}}}{e(g["icon"])}" alt="" width="44" height="44"><span>開催期間：{e(g["period"])}<br><a href="{{{{root}}}}{e(g["char_page"])}">{c}の<span class="cp-nw">データ・イベントはこちら</span></a></span></p>

  <h2 id="result">何周で完成する？</h2>
  <div class="g-dj"><p class="g-h">ダイジョーブ博士像を使う場合（枚数を選ぶ）</p><div class="g-djs">{dj}</div>
  <p class="muted">選んだ枚数の博士像を使える前提で、下の確率とシミュレータの確率が変わります。PSR像はPSR Lv50の計算だけに使います。</p></div>
  <div class="g-goal" role="group" aria-label="目標"><button type="button" data-goal="LV40">Lv40</button><button type="button" data-goal="SR45">SR Lv45</button><button type="button" data-goal="PSR50">PSR Lv50</button></div>
  <div class="g-stat"><div>50%で達成<b id="g-p50"></b><small id="g-p50s"></small></div><div>80%で達成<b id="g-p80"></b><small id="g-p80s"></small></div><div>90%で達成<b id="g-p90"></b><small id="g-p90s"></small></div></div>
  <h3>周回ごとの確率</h3>
  <div class="bt-wrap"><table class="bt g-t"><thead><tr><th scope="col">周回</th><th scope="col">Lv40</th><th scope="col">SR<br>Lv45</th><th scope="col">PSR<br>Lv50</th></tr></thead><tbody id="g-tbl"></tbody></table></div>
  <p>{loop_note}今回のガチャで出た{c}だけを使い、引き終わってから合成した場合の確率です。Lv40は「PSRが1枚以上出る」か「SRを+3まで上限開放できる」確率です。<b>SR Lv45は、出たPSRもSRに合成する前提の確率です。</b>（くわしくは下の「計算のしかた」）</p>
  <h3>SR・PSRが引ける確率</h3>
  <div class="bt-wrap"><table class="bt g-t"><thead><tr><th scope="col">ステップ</th><th scope="col">石</th><th scope="col">SRが<span class="cp-nw">1枚以上</span></th><th scope="col">PSRが<span class="cp-nw">1枚以上</span></th></tr></thead><tbody id="g-tbl2"></tbody></table></div>
  <p class="g-more"><button type="button" id="g-more2" hidden>もっと見る</button></p>
  <p>そのステップまで引いたときに、SR・PSRの{c}が1枚以上出ている確率です。石は1周目ステップ1からの合計です。</p>
  {comment}
  <h2 id="sim">引いてみる（シミュレータ）</h2>
  <p>ボタンを押すと、公式の提供割合どおりの確率で{c}が出ます。「達成できる確率」は、今の手持ち（と上で選んだ博士像）を一番成功率が高い順番で合成した場合のおおよその確率です。</p>
  <div class="g-sim">
    <div class="g-btns"><button type="button" data-pull="1">1ステップ</button><button type="button" data-pull="{len(g["steps"])}">1周</button><button type="button" data-pull="{10 * len(g["steps"])}" class="ghost">10周</button></div>
    <p class="g-next">次は <b id="g-next"></b> <button type="button" id="g-reset">リセット</button></p>
    <div class="g-stat g-stat2"><div>引いた回数<b id="g-pulls">0連</b></div><div>使った石<b id="g-stones">0個</b></div></div>
    <p class="g-h">手持ちの{c}</p>
    <div class="g-cnt">{"".join(f'<div class="g-{r}">{r}<b id="g-c{r}">0</b></div>' for r in RS)}</div>
    <p class="g-h">今の手持ちで達成できる確率</p>
    <p class="g-v">Lv40：<b id="g-vlv">0%</b></p><div class="g-bar"><i id="g-vlvb"></i></div>
    <p class="g-v">SR Lv45（PSRもSRに合成）：<b id="g-vsr">0%</b></p><div class="g-bar"><i id="g-vsrb"></i></div>
    <p class="g-v">PSR Lv50：<b id="g-vpsr">0%</b></p><div class="g-bar"><i id="g-vpsrb"></i></div>
    <div class="g-log" id="g-log" aria-live="polite"></div>
  </div>

  <h2 id="gacha">ガチャの内容</h2>
  {_steps_table(g)}
  <h3>提供割合</h3>
  {_rate_table(g)}
  <p class="muted">確率は公式の提供割合ページの表示どおり（小数第2位まで）の値で計算しています。{e(g["checked"].replace("-", "/"))}時点。</p>

  <h2 id="how">計算のしかた（注意）</h2>
  <ul>
    <li>上限開放の合成ルールは<a href="{{{{root}}}}guide/limit_break/">上限開放のルール</a>のとおりです。</li>
    <li><b>合成の順番は、手持ちのPSR・SR・PR・Rの{c}を見て、完成する確率が一番高くなる順番を全パターン調べて選んでいます</b>。1枚ずつそのまま合成するか、素材を育ててから合成するかは、手持ちの枚数とあと何段階で完成かによって変わるため、決まった順番はありません。</li>
    <li>引き終わってから、まとめて合成した場合の確率です。</li>
    <li>上限開放済みのカードは、同じレアリティで同時に1枚だけ育てる前提です。この前提のため、本当に一番良い手順の確率より、わずかに低く出ることがあります（ほとんどの場合0.1ポイント未満）。</li>
    <li>このガチャで出た{c}だけで計算しています（すでに持っている分は入れていません）。</li>
    <li>Lv40は、PSRが1枚以上出る（PSRは上限開放なしでLv40）か、SRを+3まで上限開放できる確率です。</li>
    <li><b>SR Lv45の確率は、出たPSRもSRに合成する前提の確率です</b>（PSRを合成するとSRが必ず+1）。PSRを素材にしない場合は、これより低くなります。</li>
    <li>Lv40・SR Lv45・PSR Lv50の確率は、それぞれ「手持ちを全部その目標に使った場合」の確率です。3つを同時に達成できる確率ではありません。</li>
    <li>ダイジョーブ博士像は、同じレアリティのカードの上限開放を必ず+1するアイテムとして計算しています（PSR像はPSRだけ、SR像はSRだけ、PR像はPRだけ、R像はRだけに使えます）。どのカードに、どのタイミングで使うかも、確率が一番高くなるように選んでいます。SR Lv45とLv40の計算では、PSR像は使いません。</li>
    <li>1ランク下の+5を素材にしたときの「45%で+2」は推測値です（ゲーム内で確認できないため、運営者の過去の調査によるおおよその値）。</li>
    <li>結果は確率なので、表の周回数を引いても完成しないことがあります。</li>
  </ul>
</div>
<script type="application/json" id="gdata">{json.dumps(data, ensure_ascii=False).replace("</", "<\\/")}</script>'''


def generate(src):
    pages, cards = [], []
    for f in sorted((src / "gacha").glob("*.json")):
        if f.name.endswith(".tables.json"):
            continue
        g = json.loads(f.read_text(encoding="utf-8"))
        tf = f.parent / (f.stem + ".tables.json")
        if not tf.exists():
            raise SystemExit(f"{tf.name} がありません。先に python3 gacha_calc/build_tables.py を実行してください")
        g["tables"] = json.loads(tf.read_text(encoding="utf-8"))
        path = f'gacha/{g["id"]}/'
        meta = (f'title: {g["chara"]}のガチャは引くべき？何周で完成するか計算（SR Lv45・PSR Lv50）｜パワプロアプリ攻略ベース\n'
                f'description: {g["chara"]}のガチャは引くべき？{g["title"]}で{g["chara"]}のSR Lv45・PSR Lv50を作るのに何周必要かを計算。SR・PSRが引ける確率、Lv40に届く確率、ダイジョーブ博士像を使う場合の確率と、実際に引いて試せるシミュレータつき。\n'
                f"path: {path}\nnav: home\nscripts: gacha\n")
        pages.append(f"<!--\n{meta}-->\n" + _body(g, "", src))
        cards.append((g["id"], f'<a class="scard" href="{{{{root}}}}{path}"><span class="tag p">{e(g["chara"])}</span><h3>{e(g["chara"])}のガチャは引くべき？</h3>'
                               f'<p>SR Lv45・PSR Lv50の完成確率と<span class="cp-nw">シミュレータ。</span></p><span class="go" aria-hidden="true">→</span></a>'))
    cards.sort(key=lambda x: x[0], reverse=True)   # 新しいガチャを上に
    return pages, "\n  ".join(c for _, c in cards)
