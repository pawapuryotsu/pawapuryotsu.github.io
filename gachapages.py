# ガチャ記事（/gacha/<id>/）を src/gacha/<id>.json から作る。build.py から呼ばれる。
# 新しいガチャを足すとき：src/gacha/<id>.json を作る → python3 gacha_calc/build_tables.py → python3 build.py
# id は「開始日_キャラ」（例 2026_1111_shampoo）。URLに「-」は使わない。
import html as _h, json
import charpages   # ランキングでの評価・文字の色指定を、キャラページと同じ形で出すため（build.py で charpages.generate() の後に呼ぶ）
from pathlib import Path

e = _h.escape
RS = ["PSR", "SR", "PR", "R"]


def _period(t):
    """開催期間。日付（と時刻）の途中で改行しないようにする"""
    import re
    return re.sub(r"(?:\d+年)?\d+月\d+日\(.\)(?:\d+:\d+)?", lambda m: f'<span class="cp-nw">{m.group(0)}</span>', e(t))


def _pct(v):
    return f"{v:g}%"


def _steps_table(g):
    rows = []
    for i, s in enumerate(g["steps"]):
        fixed = "<br>".join(e(x["label"]) for x in s["slots"] if x["label"] != "上記以外") or "なし"
        rows.append(f'<tr class="g-s{i % 4 + 1}"><td>{e(s["name"])}</td><td>{s["pulls"]}連</td><td>{s["cost"]}個</td><td class="g-l">{fixed}</td></tr>')
    return ('<div class="bt-wrap"><table class="bt g-t"><thead><tr><th scope="col">ステップ</th><th scope="col">連数</th>'
            '<th scope="col">石</th><th scope="col">確定枠・おまけ</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def _rate_table(g):
    rows = []
    for i, s in enumerate(g["steps"]):
        for x in s["slots"]:
            cells = "".join(f'<td>{_pct(x["rarity"][r]) if r in x["rarity"] else "—"}</td>' for r in RS)
            kind = "おまけ" if x["target"] == "pick" else "確定枠" if "確定" in x["label"] else "通常枠"
            who = (f'<wbr><span class="cp-nw">（{e(g["chara"])}のみ）</span>' if x["target"] == "only"
                   else '<wbr><span class="cp-nw">（目当てのキャラを選ぶ）</span>' if x["target"] == "pick" else "")
            rows.append(f'<tr class="g-s{i % 4 + 1}"><td class="g-l">{e(s["name"])}<br><small><span class="cp-nw">{kind}{x["n"]}枚</span>{who}</small></td>{cells}</tr>')
    share = "・".join(f'<span class="cp-nw">{r} {_pct(g["share"][r])}</span>' for r in RS if r in g["share"])
    return ('<div class="bt-wrap"><table class="bt g-t"><thead><tr><th scope="col">枠</th>' + "".join(f'<th scope="col">{r}</th>' for r in RS)
            + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            + (f'<p>{e(g["chara"])}のみの枠以外で、そのレアリティが出たときに{e(g["chara"])}の{"どちらか" if len(g["charas"]) == 2 else "いずれか"}になる割合（{len(g["charas"])}人合計。1人あたりはこの{len(g["charas"])}分の1）：{share}</p>'
               if g.get("charas") else f'<p>{e(g["chara"])}のみの枠以外で、そのレアリティが出たときに{e(g["chara"])}になる割合：{share}</p>'))


def gw(g):
    """タイトル・見出しでの呼び方。イベキャラ復刻のガチャ（json の "revival": true）は「復刻ガチャ」（管理人 2026-11-17）"""
    return "復刻ガチャ" if g.get("revival") else "ガチャ"


def _eval_html(g, src_dir):
    """「管理人の評価」。comment＝管理人の考え（文字の色指定 {太:…} などはキャラページと同じ）。
    イベキャラとしての評価は、ランキングでのランクだけ出す（評価文は長くなるので載せない。管理人 2026-11-12）"""
    com = g.get("comment") or []
    if isinstance(com, str):
        com = [com] if com else []
    chs = _chars(g)
    chara_eval = "".join(f'<div class="rk-box"><div class="rk-head"><span class="tier tier-{t}">{t}</span>'
                         f'<a href="{{{{root}}}}{r["path"]}">{e(r["短い名前"])}</a>{charpages.date_label(r)}</div></div>'
                         for ch in chs for r, t, _ in charpages.rankings_of(ch["chara"]))
    if len(chs) > 1:   # キャラごとに分けて出す
        chara_eval = "".join(f'<p class="g-h">{e(ch["chara"])}</p>' + "".join(
            f'<div class="rk-box"><div class="rk-head"><span class="tier tier-{t}">{t}</span>'
            f'<a href="{{{{root}}}}{r["path"]}">{e(r["短い名前"])}</a>{charpages.date_label(r)}</div></div>'
            for r, t, _ in charpages.rankings_of(ch["chara"])) for ch in chs if charpages.rankings_of(ch["chara"]))
    if not com and not chara_eval:
        return ""
    out = '<h2 id="eval">管理人の評価</h2>' + charpages.paras(com)
    if com and g.get("comment_date"):
        out += f'<p class="cp-evdate"><span class="rk-date">【記入日{e(g["comment_date"])}】</span></p>'
    if chara_eval:
        out += f'<h3>イベキャラとしての評価</h3>{chara_eval}' + "".join(
            f'<p><a href="{{{{root}}}}{e(ch["char_page"])}">{e(ch["chara"])}の<span class="cp-nw">ページを見る</span></a></p>' for ch in chs)
    return out


def _chars(g):
    """目当てキャラの一覧。出現率アップキャラが複数のガチャ（json の "charas"）は、キャラごとに表を作ってページで切り替える"""
    if g.get("charas"):
        return g["charas"]
    return [{"key": "", "chara": g["chara"], "char_page": g["char_page"], "icon": g["icon"], "extra": g.get("extra", []), "tables": g["tables"]}]


def _body(g, root_icon, src_dir):
    chs = _chars(g)
    multi = len(chs) > 1

    # 「2人とも」（gacha_calc/both.py の表があるとき）。切り替えボタンの最後に足す
    both = {"key": "both", "chara": g["chara"], "label": "2人とも", "both": True, "tables": g["both"],
            "extra": [dict(x, label=f'{x["label"]}（{ch["chara"]}）') for ch in chs for x in ch.get("extra", [])]} if g.get("both") else None
    views = chs + ([both] if both else [])

    def per(fn):
        """キャラによって変わる文。複数キャラのときはキャラごとに書いて、選んでいるキャラの分だけ見せる（gacha.js）"""
        if not multi:
            return fn(chs[0])
        return "".join(f'<span data-ch="{ch["key"]}"{" hidden" if i else ""}>{fn(ch)}</span>' for i, ch in enumerate(views) if fn(ch) != "")

    def only_both(t):
        """「2人とも」を選んでいるときだけ見せる"""
        return f'<span data-ch="both" hidden>{t}</span>' if both else ""

    c = per(lambda ch: e(ch["chara"]))
    data = {k: g[k] for k in ("id", "chara", "loop", "share", "steps")}
    data["charas"] = [{"key": ch["key"], "chara": ch["chara"], "extra": ch.get("extra", []), "tables": ch["tables"], "both": ch.get("both", False)} for ch in views]
    data["extra"] = chs[0].get("extra", [])
    exf = lambda ch: "・".join(f'{e(x["label"])}の{e(x["rarity"])}{x["n"]}枚' for x in ch.get("extra", []))   # 例：イベント報酬のPR1枚
    used_txt = per(lambda ch: f'今回のガチャで出た{e(ch["chara"])}と、{exf(ch)}' if exf(ch) else f'今回のガチャで出た{e(ch["chara"])}だけ')
    sim_ex = per(lambda ch: f"手持ちは{exf(ch)}が入った状態から始まります。" if exf(ch) and not ch.get("both") else "")
    data["tables"] = chs[0]["tables"]
    # 旧バージョンの手持ちの入力欄（json の "old_ver": true のガチャだけ。計算は assets/gacha_old.js がブラウザでする）
    old_box = old_notes = ""
    mix = g.get("mix")   # 別バージョン（通常版など）も同じガチャから出る（計算は gacha_calc/mix.py。シミュレータは assets/gacha_old.js）
    mix_sim = mix_cnt = mix_note = ""
    if g.get("old_ver") or mix:
        import hashlib
        data["old_v"] = hashlib.md5(b"".join((src_dir / "assets" / f).read_bytes() for f in ("gacha_old.js", "gacha_old.wasm"))).hexdigest()[:8]
    if mix:
        assert not multi, "mix は出現率アップキャラが1人のガチャだけ"
        mn, ms = e(mix["name"]), e(mix["short"])
        cap = g["tables"]["mixcap"]   # 計算に入れた枚数の上限（R, PR, SR, PSR。gacha_calc/mix.py の CAP）
        used_txt = f'今回のガチャで出た{c}と{ms}の{mn}' + (f'、{exf(chs[0])}' if exf(chs[0]) else "")   # 表の下・計算のしかたの「何を使うか」
        data["mix"] = {"n": mix["n"], "short": mix["short"]}
        mix_sim = f'このガチャでは{ms}の{mn}も出ます（上限開放の素材に使えます）。'
        mix_cnt = (f'<p class="g-v">ガチャで出た{ms}の{mn}（素材）：<b id="g-mixc">なし</b></p>'
                   f'<p class="muted" id="g-mixn" hidden>{ms}のカードが多すぎるため、{ms}を使わない場合の確率を表示しています。</p>')
        mix_note = "".join("\n    <li>" + x + "</li>" for x in [
            f'<b>このガチャでは{ms}の{mn}も出現し、上限開放の素材に使えます。上の確率は、ガチャで出た{ms}も素材に使う前提です</b>'
            f'（{ms}は、出現率アップではない{mix["n"]}人の中に入っています。公式の「それぞれの各イベキャラの出現割合は均一」により、そのレアリティが出たときの残りの割合を{mix["n"]}人で等分して計算しています）。',
            f'{ms}は「別バージョンの素材」です。同じレアリティに合成すると50%で+1（今回のバージョン同士なら100%）、1ランク下の素材として使うときは今回のバージョンと同じ確率です。'
            f'{ms}の使い方は、旧バージョンの手持ちを入れたときと同じ方法で調べています（合成の順番を全部は調べていないので、本当に一番良い手順の確率より、わずかに低く出ることがあります）。',
            f'{ms}は、R{cap[0]}枚・PR{cap[1]}枚・SR{cap[2]}枚・PSR{cap[3]}枚までを計算に入れています（それより多く出た分は使わない計算です。確率への影響はごくわずかです）。'
            f'博士像は{ms}のカードには使わない計算です。'])
    if g.get("old_ver"):
        rows = "".join(f'<tr><th scope="row" class="g-{r}">{r}</th>' + "".join(
            f'<td><input type="number" inputmode="numeric" min="0" max="9" data-old="{3 - i}_{l}" autocomplete="off" aria-label="旧バージョンの{r}+{l}の枚数"></td>' for l in range(6))
            + "</tr>" for i, r in enumerate(RS))
        old_box = (f'<div class="g-dj g-old" data-nb><p class="g-h">旧バージョンの{e(g.get("old_name") or c)}を持っている場合（枚数を入れる）</p>'
                   '<table class="g-oldt"><thead><tr><th></th>' + "".join(f'<th scope="col">+{l}</th>' for l in range(6)) + f'</tr></thead><tbody>{rows}</tbody></table>'
                   '<p class="g-oldb"><button type="button" id="g-oldgo">計算する</button><button type="button" id="g-oldclr" class="ghost">クリア</button></p>'
                   '<p class="g-olds" id="g-olds" aria-live="polite"></p>'
                   '<p class="muted">+0〜+5は上限開放の段階です。持っている旧バージョンのカードを素材として使う前提で、下の確率とシミュレータの確率が変わります'
                   '（完成させるのは今回のバージョンです）。旧バージョンが2種類以上あるときは、まとめて入れてください。<br>'
                   '<b><span class="cp-nw">旧バージョン込みの確率は、</span><span class="cp-nw">実際より少し低めに</span><span class="cp-nw">出ることがあります</span></b><span class="cp-nw">（くわしくは下の</span><span class="cp-nw">「計算のしかた」）。</span></p></div>')
        old_notes = "".join("\n    <li>" + x + "</li>" for x in [
            "<b>旧バージョンの手持ちを入れたとき</b>：旧バージョンのカードは素材として使います（完成させるのは今回のバージョンのカードです）。旧バージョンが2種類以上あっても、まとめて1つの旧バージョンとして計算します。",
            "旧バージョンを同じレアリティに合成するときの確率（+0で50%〜+4で100%、+5は75%で+3・25%で+2）のうち、<b>+5素材の「75%で+3」は推測値です</b>（ゲーム内で確認できないため、運営者の過去の調査によるおおよその値）。",
            "<b>上限開放済みの旧バージョンのPSRは、今回のバージョンのSRには合成しない前提です</b>（上のランクの素材が上限開放済みのときの確率は未検証のため。+0の旧PSRは、SRに合成すると必ず+1として計算します）。",
            "旧バージョン同士を先に合成して育ててから素材にする手順（同じバージョン同士は100%で+1）や、上限開放が途中の旧バージョンのカードに今回のバージョンのカードを合成して育てる手順も、計算に入れています。",
            "<b>旧バージョン込みの確率は、合成の順番を全パターン調べた値ではありません</b>（組み合わせが多すぎて、その場では計算できないため）。「旧バージョンのカードを先に使い、残りを今までどおり一番成功率が高い順番で合成する」方法の中で一番良い手順の確率なので、本当に一番良い手順の確率より少し低く出ることがあります（時間をかけた計算と比べた範囲では、周回ごとの確率で最大1ポイントほど）。そのため1%きざみで表示しています。",
            "旧バージョン込みの計算では、ダイジョーブ博士像は旧バージョンのカードには使いません（今回のバージョンのカードに使います）。"])
    picks = [(s["name"], x) for s in g["steps"] for x in s["slots"] if x["target"] == "pick"]
    pick_note = ("・".join(f'{e(n)}の{e(x["label"].replace("おまけ：", ""))}' for n, x in picks)
                 + ("は毎周もらえ、" if g.get("loop") else "は、") + "すべて" + ("表示中のキャラ" if multi else c) + "を選ぶ前提で計算しています。") if picks else ""
    ch_btns = ('<div class="g-goal g-chs" role="group" aria-label="キャラ">'
               + "".join(f'<button type="button" data-chb="{ch["key"]}">{e(ch.get("label", ch["chara"]))}</button>' for ch in views)
               + '</div><p class="muted">キャラを切り替えると、下の確率とシミュレータが切り替わります。</p>') if multi else ""
    metas = "".join(f'<p class="g-meta">' + (f'<img src="{{{{root}}}}{e(ch["icon"])}" alt="" width="44" height="44">' if ch.get("icon") else "") + '<span>'
                    + (f'開催期間：{_period(g["period"])}<br>' if not multi else "")
                    + f'<a href="{{{{root}}}}{e(ch["char_page"])}">{e(ch["chara"])}の<span class="cp-nw">データ・イベントはこちら</span></a></span></p>' for ch in chs)
    if multi:
        metas = f'<p>開催期間：{_period(g["period"])}</p>' + metas
    # 見出し：キャラ名の途中で改行しないように、名前ごとに区切る
    h1 = ("".join(f'<i>{e(ch["chara"])}{"・" if i < len(chs) - 1 else "の"}</i>' for i, ch in enumerate(chs)) + f" <i>{gw(g)}は</i> <i>引くべき？</i>"
          if multi else f'<i>{e(g["chara"])}の</i><i>{gw(g)}は</i> <i>引くべき？</i>' if len(g["chara"]) >= 8   # 長い名前はスマホで名前の途中で折り返さないよう分ける
          else f'<i>{e(g["chara"])}の{gw(g)}は</i> <i>引くべき？</i>')
    nm = lambda ch: e(ch.get("short", ch["chara"]))
    both_notes = [
        "選択ガチャ券は取っておき、引き終わってから、2人とも完成する確率が一番高くなるように2人に分けて使います（1人ずつの確率では、券を全部そのキャラに使います）。",
        f'{"、".join(f"{nm(ch)}の手持ちは{nm(ch)}だけに" for ch in chs)}使います。合成の順番は、それぞれ1人ずつのときと同じく一番成功率が高い順番です。'
        + "".join(f'{e(x["label"])}の{e(x["rarity"])}{x["n"]}枚は{nm(ch)}に使います。' for ch in chs for x in ch.get("extra", [])),
        "ダイジョーブ博士像は使わない計算です（そのため博士像の枚数の欄は出しません）。",
        f'2人分の手持ちの組み合わせが多すぎて全パターンを計算できないため、ガチャを{g["both"]["mc"] // 10000}万回試しに引いた結果の割合です（誤差は0.3ポイントほど）。そのため100%にはせず「ほぼ100%」と表示します。' if both else "",
        "Lv40・SR Lv45・PSR Lv50は、それぞれ「2人ともその目標に届く」確率です。"] if both else []
    both_box = ('<div class="g-note" data-ch="both" hidden><p class="g-h">※「2人とも」の確率は、1人ずつのときと次の点が違います</p><ul>'
                + "".join(f"<li>{x}</li>" for x in both_notes) + "</ul></div>") if both else ""
    more_notes = "".join("\n    <li>" + x + "</li>" for x in [
        pick_note,
        f'出現率アップの割合は{e(g["chara"])}の{len(chs)}人合計なので、1人あたりはその{len(chs)}分の1で計算しています（公式の「各レアリティ内の各イベキャラの出現割合は均一」による）。「{e(g["chara"]).replace("・", "」または「")}」の確定枠も{len(chs)}人で等分です。' if multi else "",
        "キャラごとの確率は、手持ちを全部そのキャラに使った場合の確率です。" + ("2人とも" if len(chs) == 2 else "2人以上") + "育てる場合は、選択ガチャ券を分けるぶん確率が下がります" + ("（「2人とも」を選ぶと、2人とも完成する確率を表示します）。" if both else "。") if multi and picks else "",
        ("「2人とも」の確率は、1人ずつのときと計算のしかたが違います：" + "".join(both_notes)) if both else ""] + g.get("notes", []) if x)   # notes：そのガチャだけの注意（json に書く）
    loop_note = (f'1周＝{"〜".join([g["steps"][0]["name"], g["steps"][-1]["name"]])}'
                 f'（{sum(s["pulls"] for s in g["steps"])}連・<span class="cp-nw">パワストーン{sum(s["cost"] for s in g["steps"])}個</span>）。<br>') if g.get("loop") else ""
    comment = _eval_html(g, src_dir)
    kmax = {"PSR": g["tables"]["KS"], "SR": g["tables"]["KS"], "PR": g["tables"]["KL"], "R": g["tables"]["KL"]}
    dj = "".join(f'<label><span class="g-{r}">{r}像</span><select data-dj="{r}" autocomplete="off" aria-label="{r}ダイジョーブ博士像の枚数">'
                 + "".join(f'<option value="{i}">{i}枚</option>' for i in range(kmax[r] + 1)) + "</select></label>" for r in RS)
    # g["sources"]（公式ページのURL）は記録用。ゲーム内のページなので記事にはリンクを載せない（2026-11-12 管理人）
    return f'''<section class="phead"><p class="eyebrow">ガチャ</p><h1><span class="mk">{h1}</span></h1><p>{e(g["title"])}で、{e(g["chara"])}のSR Lv45・PSR Lv50を作るのに何周必要かを<span class="cp-nw">計算しました。</span>引くべきか迷っている人は、下の確率と<span class="cp-nw">石の数を目安にしてください。</span></p></section>
<div class="prose">
  <div class="g-info">{metas}</div>
  {comment}

  <h2 id="result">何周で完成する？</h2>
  {ch_btns}
  <div class="g-dj" data-nb><p class="g-h">ダイジョーブ博士像を使う場合（枚数を選ぶ）</p><div class="g-djs">{dj}</div>
  <p class="muted">選んだ枚数の博士像を使える前提で、下の確率とシミュレータの確率が変わります。PSR像はPSR Lv50の計算だけに使います。</p></div>
  {old_box}
  <div class="g-goal" role="group" aria-label="目標"><button type="button" data-goal="LV40">Lv40</button><button type="button" data-goal="SR45">SR Lv45</button><button type="button" data-goal="PSR50">PSR Lv50</button></div>
  <div class="g-stat"><div>50%で達成<b id="g-p50"></b><small id="g-p50s"></small></div><div>80%で達成<b id="g-p80"></b><small id="g-p80s"></small></div><div>90%で達成<b id="g-p90"></b><small id="g-p90s"></small></div></div>
  <h3>周回ごとの確率</h3>
  <div class="bt-wrap"><table class="bt g-t"><thead><tr><th scope="col">周回</th><th scope="col">Lv40</th><th scope="col">SR<br>Lv45</th><th scope="col">PSR<br>Lv50</th></tr></thead><tbody id="g-tbl"></tbody></table></div>
  <p>{loop_note}{used_txt}を使い、引き終わってから<span class="cp-nw">合成した場合の</span><span class="cp-nw">確率です。</span><br>Lv40は「PSRが1枚以上出る」か<span class="cp-nw">「SRを+3まで</span><span class="cp-nw">上限開放できる」</span><span class="cp-nw">確率です。</span><br><b>SR Lv45は、出たPSRもSRに<span class="cp-nw">合成する</span><span class="cp-nw">前提の確率です。</span></b><br>（くわしくは下の<span class="cp-nw">「計算のしかた」）</span></p>
  {both_box}
  <h3>SR・PSRが引ける確率</h3>
  <div class="bt-wrap"><table class="bt g-t"><thead><tr><th scope="col">ステップ</th><th scope="col">石</th><th scope="col">SRが<span class="cp-nw">1枚以上</span></th><th scope="col">PSRが<span class="cp-nw">1枚以上</span></th></tr></thead><tbody id="g-tbl2"></tbody></table></div>
  <p>そのステップまで引いたときに、{per(lambda ch: "2人ともSR・PSRが1枚以上ある確率です（選択ガチャ券は足りない方に使う前提）" if ch.get("both") else f"SR・PSRの{e(ch['chara'])}が1枚以上出ている確率です")}。石は1周目ステップ1からの合計です。</p>
  <h2 id="sim">引いてみる（シミュレータ）</h2>
  {only_both('<p class="g-note">シミュレータは1人ずつです。上のボタンで' + "・".join(e(ch["chara"]) for ch in chs) + 'を選ぶと使えます。</p>')}
  <div data-nb>
  <p>ボタンを押すと、公式の提供割合どおりの確率で{c}が出ます。{mix_sim}{sim_ex}「達成できる確率」は、今の手持ち（と上で選んだ博士像）を一番成功率が高い順番で合成した場合のおおよその確率です。</p>
  <div class="g-sim">
    <div class="g-btns"><button type="button" data-pull="1">1ステップ</button><button type="button" data-pull="{len(g["steps"])}">1周</button><button type="button" data-pull="{10 * len(g["steps"])}" class="ghost">10周</button></div>
    <p class="g-next">次は <b id="g-next"></b> <button type="button" id="g-reset">リセット</button></p>
    <div class="g-stat g-stat2"><div>引いた回数<b id="g-pulls">0連</b></div><div>使った石<b id="g-stones">0個</b></div></div>
    <p class="g-h">手持ちの{c}</p>
    <div class="g-cnt">{"".join(f'<div class="g-{r}">{r}<b id="g-c{r}">0</b></div>' for r in RS)}</div>
    {mix_cnt}<p class="g-h">今の手持ちで達成できる確率</p>
    <p class="g-v">Lv40：<b id="g-vlv">0%</b></p><div class="g-bar"><i id="g-vlvb"></i></div>
    <p class="g-v">SR Lv45（PSRもSRに合成）：<b id="g-vsr">0%</b></p><div class="g-bar"><i id="g-vsrb"></i></div>
    <p class="g-v">PSR Lv50：<b id="g-vpsr">0%</b></p><div class="g-bar"><i id="g-vpsrb"></i></div>
    <div class="g-log" id="g-log" aria-live="polite"></div>
  </div>
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
    <li>{used_txt}で計算しています（それ以外にすでに持っている分は入れていません）。</li>{mix_note}{more_notes}
    <li>Lv40は、PSRが1枚以上出る（PSRは上限開放なしでLv40）か、SRを+3まで上限開放できる確率です。</li>
    <li><b>SR Lv45の確率は、出たPSRもSRに合成する前提の確率です</b>（PSRを合成するとSRが必ず+1）。PSRを素材にしない場合は、これより低くなります。</li>
    <li>Lv40・SR Lv45・PSR Lv50の確率は、それぞれ「手持ちを全部その目標に使った場合」の確率です。3つを同時に達成できる確率ではありません。</li>
    <li>ダイジョーブ博士像は、同じレアリティのカードの上限開放を必ず+1するアイテムとして計算しています（PSR像はPSRだけ、SR像はSRだけ、PR像はPRだけ、R像はRだけに使えます）。どのカードに、どのタイミングで使うかも、確率が一番高くなるように選んでいます。SR Lv45とLv40の計算では、PSR像は使いません。</li>
    <li>1ランク下の+5を素材にしたときの「45%で+2」は推測値です（ゲーム内で確認できないため、運営者の過去の調査によるおおよその値）。</li>{old_notes}
    <li>結果は確率なので、表の周回数を引いても完成しないことがあります。</li>
  </ul>
</div>
<script type="application/json" id="gdata">{json.dumps(data, ensure_ascii=False).replace("</", "<\\/")}</script>'''


def generate(src):
    pages, cards, past_rows = [], [], []
    for f in sorted((src / "gacha").glob("*.json")):
        if f.name.endswith(".tables.json"):
            continue
        g = json.loads(f.read_text(encoding="utf-8"))
        def load(stem):
            tf = f.parent / (stem + ".tables.json")
            if not tf.exists():
                raise SystemExit(f"{tf.name} がありません。先に python3 gacha_calc/build_tables.py を実行してください")
            return json.loads(tf.read_text(encoding="utf-8"))
        if g.get("charas"):
            for ch in g["charas"]:
                ch["tables"] = load(f"{f.stem}_{ch['key']}")
            g["tables"] = g["charas"][0]["tables"]
            if (f.parent / (f.stem + "_both.tables.json")).exists():   # 2人とも（gacha_calc/both.py）
                g["both"] = load(f.stem + "_both")
        else:
            g["tables"] = load(f.stem)
        path = f'gacha/{g["id"]}/'
        meta = (f'title: {g["chara"]}の{gw(g)}は引くべき？何周で完成するか計算（SR Lv45・PSR Lv50）｜パワプロアプリ攻略ベース\n'
                f'description: {g["chara"]}の{gw(g)}は引くべき？{g["title"]}で{g["chara"]}のSR Lv45・PSR Lv50を作るのに何周必要かを計算。SR・PSRが引ける確率、Lv40に届く確率、ダイジョーブ博士像を使う場合の確率と、実際に引いて試せるシミュレータつき。\n'
                f"path: {path}\nnav: home\nscripts: gacha\ncrumb: {g['chara']}のガチャ\n"
                f"og_title: {g['chara']}の{gw(g)}は引くべき？\nrecent_title: {g['chara']}の{gw(g)}は引くべき？\nog_icon: {(g.get('charas') or [g])[0].get('icon', '')}\n")
        pages.append(f"<!--\n{meta}-->\n" + _body(g, "", src))
        # カードにイベキャラのアイコンを付ける（json の icon、2キャラのガチャは charas の icon を全員分。2026-11-24 管理人）
        icons = "".join(f'<img src="{{{{root}}}}{e(ch["icon"])}" alt="" width="48" height="48" loading="lazy">' for ch in (g.get("charas") or [g]) if ch.get("icon"))
        cards.append((g["id"], _ended(g), f'<a class="scard gcard" href="{{{{root}}}}{path}">' + (f'<span class="gc-icons">{icons}</span>' if icons else "") + f'<span class="tag p">{e(g["chara"])}</span><h3><span class="cp-nw">{e(g["chara"])}の</span><span class="cp-nw">{gw(g)}は</span><span class="cp-nw">引くべき？</span></h3>'
                               f'<p>SR Lv45・PSR Lv50の完成確率と<span class="cp-nw">シミュレータ。</span></p><span class="go" aria-hidden="true">→</span></a>'))
        if _ended(g):
            past_rows.append((_end_dt(g), g, path))
    cards.sort(key=lambda x: x[0], reverse=True)   # 新しいガチャを上に
    past_rows.sort(key=lambda x: (x[0] is not None, x[0] or 0, x[1]["id"]), reverse=True)   # 過去のガチャは終了日時が新しい順（2026-11-25 管理人）
    pages.append(_past_page(past_rows))
    now = [c for _, ended, c in cards if not ended] + [PAST_CARD]
    return pages, "\n  ".join(now)


# 「過去のガチャ」ページ（/gacha/past/、2026-11-17 管理人）。ガチャ期間が終わったガチャの記事のカードをここに並べる。
# 期間が終わったかどうかは json の period の終了日時（日本時間）と build.py を実行した時刻で自動で決める。
# json に "past": true / false を書けば、そちらを優先する（手で移したい・戻したいとき用）。
# まだ終わったガチャが無いので noindex（管理人指示）。トップ「最近の更新」にも出さない（src/home_updates.json）。
PAST_PATH = "gacha/past/"
PAST_NOINDEX = True
PAST_CARD = (f'<a class="scard" href="{{{{root}}}}{PAST_PATH}"><h3>過去のガチャ</h3>'
             f'<p>ガチャ期間が終了したガチャの<span class="cp-nw">記事をまとめています。</span></p><span class="go" aria-hidden="true">→</span></a>')


def _period_dt(g):
    """period から（開始日時, 終了日時）を日本時間で取り出す。終了は 13:59 まで → 14:00 とする。読めなければ None"""
    import re
    from datetime import datetime, timedelta, timezone
    m = re.match(r"(\d+)年(\d+)月(\d+)日\(.\)(?:(\d+):(\d+))?[^〜]*〜(?:(\d+)年)?(\d+)月(\d+)日\(.\)(\d+):(\d+)", g.get("period", ""))
    if not m:
        return None
    y0, m0, d0, h0, n0, y1, mo, d, hh, mm = m.groups()
    y = int(y1) if y1 else int(y0) + (1 if int(mo) < int(m0) else 0)   # 終了日に年が無ければ開始の年（年をまたぐときは次の年）
    jst = timezone(timedelta(hours=9))
    start = datetime(int(y0), int(m0), int(d0), int(h0 or 0), int(n0 or 0), tzinfo=jst)   # 「メンテナンス終了後」など時刻が無いときは0時
    end = datetime(y, int(mo), int(d), int(hh), int(mm), tzinfo=jst) + timedelta(minutes=1)
    return start, end


def _end_dt(g):
    p = _period_dt(g)
    return p[1] if p else None


def _ended(g, now=None):
    from datetime import datetime, timedelta, timezone
    if "past" in g:
        return bool(g["past"])
    end = _end_dt(g)
    if end is None:
        return False
    return (now or datetime.now(timezone(timedelta(hours=9)))) >= end


def _period_label(g):
    """表の「ガチャ期間」。例 2026/11/16～12/4（年をまたぐときは終了側にも年を付ける）"""
    p = _period_dt(g)
    if not p:
        return e(g.get("period", ""))
    s, t = p
    from datetime import timedelta
    t = t - timedelta(minutes=1)   # 表示は最終日（13:59 の日）
    end = f"{t.year}/{t.month}/{t.day}" if t.year != s.year else f"{t.month}/{t.day}"
    return f'<span class="cp-nw">{s.year}/{s.month}/{s.day}～</span><span class="cp-nw">{end}</span>'


def _name_html(name):
    """[エアギター]志藤玲美 → 「[エアギター]」と「志藤玲美」の間でだけ折り返す"""
    import re
    m = re.match(r"(\[[^\]]*\])(.+)", name)
    if not m:
        return f'<span class="cp-nw">{e(name)}</span>'
    return f'<span class="cp-nw">{e(m.group(1))}</span><wbr><span class="cp-nw">{e(m.group(2))}</span>'


def _past_page(rows):
    """rows＝［(終了日時, ガチャjson, 記事のパス)］終了日時が新しい順。
    表は「イベキャラのアイコン | イベキャラ名 | ガチャ開始日～終了日 | 評価」（2026-11-25 管理人）。
    評価はガチャ記事の「イベキャラとしての評価」と同じ、ランキングでのランク（build した時点のもの）"""
    meta = (f"title: 過去のガチャ（期間終了したガチャの記事まとめ）｜パワプロアプリ攻略ベース\n"
            f"description: パワプロアプリで2026年11月以降に追加されたガチャのうち、ガチャ期間が終了したものの「引くべき？」記事をまとめています。\n"
            f"path: {PAST_PATH}\nnav: home\ncrumb: 過去のガチャ\n" + ("noindex: yes\n" if PAST_NOINDEX else ""))
    body = ('<section class="phead"><p class="eyebrow">ガチャ</p><h1><span class="mk"><i>過去のガチャ</i></span></h1>'
            '<p><span class="cp-nw">2026年11月以降に</span><span class="cp-nw">追加されたガチャの、</span><span class="cp-nw">ガチャ期間が</span><span class="cp-nw">終了したガチャの</span>'
            '<span class="cp-nw">「引くべき？」記事を</span><span class="cp-nw">まとめています。</span></p></section>\n')
    if not rows:
        return f"<!--\n{meta}-->\n" + body + '<div class="prose"><p>まだ期間が終了したガチャは<span class="cp-nw">ありません。</span></p></div>\n'
    trs = []
    for _, g, path in rows:
        chs = g.get("charas") or [g]
        icons = "".join(f'<img src="{{{{root}}}}{e(ch["icon"])}" alt="" width="44" height="44" loading="lazy">' for ch in chs if ch.get("icon"))
        names = "".join(f'<span class="gp-nm">{_name_html(ch["chara"])}</span>' for ch in chs)
        evals = ""
        for ch in chs:
            rk = "".join(f'<span class="gp-rk"><span class="tier tier-{t}">{t}</span><span class="gp-rn">{e(r["短い名前"])}</span></span>'
                         for r, t, _ in charpages.rankings_of(ch["chara"]))
            if len(chs) > 1 and rk:
                rk = f'<span class="gp-who">{e(ch["chara"])}</span>' + rk
            evals += rk
        trs.append(f'<tr><td class="gp-ic"><a href="{{{{root}}}}{path}">{icons}</a></td>'
                   f'<td class="gp-name"><a href="{{{{root}}}}{path}">{names}</a></td>'
                   f'<td class="gp-pd">{_period_label(g)}</td>'
                   f'<td class="gp-ev">{evals or "－"}</td></tr>')
    body += ('<div class="prose"><div class="tablewrap"><table class="gpast"><thead><tr><th class="gp-ic" aria-label="アイコン"></th><th>イベキャラ</th><th>ガチャ期間</th><th>評価</th></tr></thead>\n<tbody>\n'
             + "\n".join(trs) + '\n</tbody></table></div>\n'
             '<p class="muted">イベキャラ名を押すと、そのガチャの「引くべき？」記事を開きます。評価はランキングでのランクです。</p></div>\n')
    return f"<!--\n{meta}-->\n" + body
