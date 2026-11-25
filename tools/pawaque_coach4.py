"""西球記「おすすめ契約書&コーチ+4厳選解説」（旧「コーチ+4を狙うには？」）（/pawaque/saikyuki/coach4/）の本文を作る（2026-11-22 管理人）。

使い方： python3 tools/pawaque_coach4.py → python3 build.py
- 文章：src/pawaque_data/saikyuki_coach4.json（管理人の原稿。{青太:…}{赤太:…}{赤:…} が使える）
- 数字：契約書シミュレータ docs/pawaque/contract_simulator/index.html の契約書・キャラ・アイコン・理論値ランキング
        （限界Lv＝図鑑なしの契約書の値、コスト＝白袋、理論値＝コーチ+4・図鑑PSR・特訓値最大。投手は先発と西球記先発、野手はスタメン）
- 対戦相手と候補数：src/pawaque_data/saikyuki_shinzen.json
- アイコン：src/img/pawaque/coach4/ に書き出す
- 「期限」があるキャラ（コラボ）は、期限を過ぎていれば最初から出さず、ページを開いている間に期限が来たらスクリプトで消す。
src/pages/pawaque-saikyuki-coach4.html の <!-- C4:START --> 〜 <!-- C4:END --> を書き換える。数字は推測で入れない（無い値は「調査中」）。
"""
import base64, datetime as _dt, hashlib, html, json, pathlib, re

here = pathlib.Path(__file__).resolve().parent.parent
JST = _dt.timezone(_dt.timedelta(hours=9))
NOW = _dt.datetime.now(JST)
D = json.loads((here / "src/pawaque_data/saikyuki_coach4.json").read_text(encoding="utf-8"))
SH = json.loads((here / "src/pawaque_data/saikyuki_shinzen.json").read_text(encoding="utf-8"))
SIM = (here / "docs/pawaque/contract_simulator/index.html").read_text(encoding="utf-8")


def grab(key):
    i = SIM.index(key) + len(key)
    return json.JSONDecoder().raw_decode(SIM[i:].lstrip())[0]


CONS, CHARS, ICONS, TRANK = grab('"contracts":'), grab('"chars":'), grab("ICONS ="), grab("const TRANK =")
CON = {}
for c in CONS:
    CON.setdefault(c["名前"], c)
    for m in c.get("一致", []):
        CON.setdefault(m, c)
CH = {c["name"]: c for c in CHARS}
e = lambda s: html.escape(str(s), quote=True)


def rk(key, n):
    x = [y for y in TRANK.get(key, []) if y["name"] == n and y["sub"] is None]
    return x[0]["total"] if x else None


def norm(raw):
    return raw.replace("［", "[").replace("］", "]").removesuffix("の契約書")


# 対戦相手（スカウト候補の表記 → (学校, 候補数)）。期限付きの学校も入れる
TEAM = {}
for t in SH["対戦相手"]:
    for raw in t.get("固有スカウト選手候補", []):
        TEAM[norm(raw)] = (t["対戦相手"].replace("野球流", ""), len(t["固有スカウト選手候補"]))

# アイコン（data: URI → ファイル）
icon_dir = here / "src/img/pawaque/coach4"
icon_dir.mkdir(parents=True, exist_ok=True)


def icon(n):
    uri = ICONS.get(n)
    if not uri:
        return ""
    head, b64 = uri.split(",", 1)
    ext = "webp" if "webp" in head else ("png" if "png" in head else "jpg")
    raw = base64.b64decode(b64)
    fn = f"i_{hashlib.sha1(n.encode()).hexdigest()[:10]}.{ext}"
    p = icon_dir / fn
    if not p.exists() or p.read_bytes() != raw:
        p.write_bytes(raw)
    return f'<img class="c4-ic" src="{{{{root}}}}img/pawaque/coach4/{fn}" alt="" width="40" height="40" loading="lazy">'


def nm(n):
    if not n.startswith("["):
        return f'<span class="c4-v">{e(n)}</span>'
    b, rest = n[1:].split("]", 1)
    return f'<span class="c4-v"><span class="c4-vb">［{e(b)}］</span>{e(rest)}</span>'


def num(v):
    return '<span class="c4-tbd">調査中</span>' if v is None else f"{v:,}"


def rich(s):
    s = e(s)
    s = re.sub(r"\{青太:(.*?)\}", r'<b class="em-blue">\1</b>', s)
    s = re.sub(r"\{赤太:(.*?)\}", r'<b class="em-red">\1</b>', s)
    s = re.sub(r"\{赤:(.*?)\}", r'<span class="tx-red">\1</span>', s)
    return s.replace("|", "<br>")


def end_of(n):
    d = D.get("期限", {}).get(n)
    return _dt.datetime.fromisoformat(d) if d else None


# ---------- 1. 本文 ----------
def sec1():
    out = []
    for para in D["1の本文"].split("\n\n"):
        buf = []
        for line in para.split("\n"):
            m = re.match(r"\[画像:(.*)\]$", line)
            if m:
                if buf:
                    out.append("<p>" + "<br>".join(buf) + "</p>"); buf = []
                f, alt, cap = D["1の画像"][m.group(1)]
                out.append(f'<img class="pq-img" src="{{{{root}}}}img/pawaque/{f}" alt="{e(alt)}" loading="lazy">')
                if cap:
                    out.append(f'<p class="pq-cap">{rich(cap)}</p>')
            else:
                buf.append(rich(line))
        if buf:
            out.append("<p>" + "<br>".join(buf) + "</p>")
    return "\n".join(out)


# ---------- 2・3 おすすめ（カード） ----------
def rec_card(x):
    n = x["名前"]
    end = end_of(n)
    if end and NOW >= end:
        return ""
    cc, isP = CON[n], CH[n]["ポジション"] == "投"
    if "対戦相手" in x:
        team = e(x["対戦相手"])
    else:
        t, c = TEAM[x.get("スカウト候補の表記", n)]
        team = f"{e(t)}(候補{c}人)"
    val = rk("投手smain" if isP else "野手main", n)
    end_attr = f' data-end="{end.isoformat()}"' if end else ""
    return (f'<div class="c4-rc"{end_attr}><div class="c4-rch">{icon(n).replace("c4-ic", "c4-ic c4-ic-l")}<span class="c4-rcn">{nm(n)}</span></div>'
            f'<table class="c4-kv"><tr><th>対戦相手</th><td>{team}</td></tr>'
            f'<tr><th>限界Lv(図鑑未登録時)</th><td>{cc["限界Lv"]}</td></tr>'
            f'<tr><th>コスト(白袋)</th><td>{num(cc["コスト"])}</td></tr>'
            f'<tr><th>{"理論値(西球記先発)" if isP else "理論値(スタメン)"}</th><td><b class="c4-g">{num(val)}</b></td></tr></table>'
            + "".join(f"<p>{rich(t)}</p>" for t in x["文"]) + "</div>")


def rec(key):
    return (f'<h3>投手</h3><div class="c4-rcs">' + "".join(rec_card(x) for x in D[key + "の投手"]) + "</div>"
            f'<h3>野手</h3><div class="c4-rcs">' + "".join(rec_card(x) for x in D[key + "の野手"]) + "</div>")


# ---------- 4・5 一覧の表 ----------
ORDER = [("投", "投手"), ("捕", "捕手"), ("一", "一塁手"), ("二", "二塁手"), ("三", "三塁手"), ("遊", "遊撃手"), ("外", "外野手")]


def entry(n, where, mark=""):
    c, cc = CH[n], CON[n]
    pos = c["ポジション"]
    sub = '<span class="c4-sep">・</span>'.join(f'<span class="c4-sp">{p}{v}</span>' for p, v in c["サブ"].items()) or "無し"
    return dict(n=n, where=where, mark=mark, pos=pos, sub=sub, lv=cc["限界Lv"], cost=cc["コスト"],
                a=rk("投手main" if pos == "投" else "野手main", n), b=rk("投手smain", n) if pos == "投" else None)


def tables(L, wl):
    out = []
    for p, label in ORDER:
        g = sorted([x for x in L if x["pos"] == p], key=lambda x: -(x["a"] or 0))
        if not g:
            continue
        isP = p == "投"
        h = (f'<h3>{label}<span class="c4-cnt">{len(g)}人</span></h3><div class="bt-wrap"><table class="c4-t"><thead><tr><th>キャラ</th>'
             + ("" if isP else "<th>サブ</th>")
             + f'<th class="r">限界<br class="c4-mb">Lv</th><th class="r">コスト</th><th>{wl}</th>'
             + ('<th class="r">理論値<br><small>先発</small></th><th class="r">理論値<br><small>西球記先発</small></th>' if isP else '<th class="r">理論値</th>')
             + "</tr></thead><tbody>")
        for x in g:
            h += f'<tr><td class="c4-ch">{icon(x["n"])}<span>{nm(x["n"])}{"<sup>" + x["mark"] + "</sup>" if x["mark"] else ""}</span></td>'
            if not isP:
                h += f'<td class="c4-tm">{x["sub"]}</td>'
            h += f'<td class="r">{x["lv"]}</td><td class="r">{num(x["cost"])}</td><td class="c4-tm">{x["where"]}</td><td class="r"><b>{num(x["a"])}</b></td>'
            if isP:
                h += f'<td class="r"><b class="c4-g">{num(x["b"])}</b></td>'
            h += "</tr>"
        out.append(h + "</tbody></table></div>")
    return "\n".join(out)


extra = set(D.get("4に足す［］なしの別バージョン", []))
A, seen = [], set()
for t in SH["対戦相手"]:
    for raw in t.get("固有スカウト選手候補", []):
        k = norm(raw)
        if not (k.startswith("[") or k in extra):
            continue
        # 神前試合まとめが苗字だけの表記（［匠の技］堂江 など）は、同じバージョンの契約書が1人だけの時だけフルネームにする
        cand = [c for c in CH if c.startswith(k) and c in CON]   # 契約書があるキャラだけ（SR版などの別データは数えない）
        n = k if k in CH else (cand[0] if len(cand) == 1 else None)
        if not n:
            print("※契約書が決まらない（推測しないので飛ばす）:", k)
            continue
        if n in seen:
            continue
        seen.add(n)
        A.append(entry(n, e(t["対戦相手"].replace("野球流", "")), "＊" if k in extra else ""))
for raw in SH.get("全員加入の契約書", []):
    k = norm(raw)
    if k.startswith("[") and k not in seen:
        seen.add(k)
        A.append(entry(k, "全員加入"))
B = []
for x in D["5のキャラ"]:
    w = "・".join(f'<span class="tx-red">{e(q["名前"])}※注</span>' if q["注"] else e(q["名前"]) for q in x["クエスト"])
    B.append(entry(x["名前"], w, x.get("マーク", "")))

SECS = [
    ("s1", "コーチ人数+4を狙うには？", sec1()),
    ("s2", "おすすめの別バージョン契約書", f'<p>{rich(D["2の本文"])}</p>' + rec("2")),
    ("s3", "おすすめ通常バージョン契約書", f'<p>{rich(D["3の本文"])}</p>' + rec("3")),
    ("s4", "神前試合で入手できる別バージョンキャラ一覧", f'<p>{rich(D["4の本文"])}</p>' + tables(A, "対戦相手")
     + '<p class="c4-note">＊ アフロ猪狩は［　］が付きませんが、猪狩守の別バージョンなので入れています。</p>'),
    ("s5", "神前試合以外で入手できる別バージョンキャラ一覧",
     f'<p>西球記の周回記録（{D["5の周回数"]}周分）でドロップした別バージョンの契約書のうち、4の表にいないキャラ（{len(B)}人）。</p>'
     + tables(B, "ドロップしたクエスト") + '<p class="tx-red c4-note"><b>※現在エリア最終ボスでしかドロップを確認できていないので注意</b></p>'
     + "".join(f'<p class="c4-note">{e(x["マーク"])} {rich(x["補足"])}</p>' for x in D["5のキャラ"] if x.get("補足"))
     + (f'<p class="c4-note">{rich(D["5の未登録"])}</p>' if D.get("5の未登録") else "")),
]
toc = ('  <nav class="toc" aria-label="このページの目次">\n  <b>もくじ</b>\n  <ol>\n'
       + "".join(f'    <li><a href="#{i}">{t}</a></li>\n' for i, t, _ in SECS) + "  </ol>\n  </nav>\n")
body = toc + "\n".join(f'  <h2 id="{i}">{i[1]}. {t}</h2>\n{b}' for i, t, b in SECS)
body += ('\n  <p class="c4-note">理論値は契約書シミュレータの理論値ランキングと同じ条件（コーチ+4・図鑑PSR・上限突破なし・特訓値最大）で、メインポジションの値です。'
         '野手はスタメンの値です。限界Lvは契約書そのままの値（図鑑の上乗せなし）、コストは白袋の値です。「調査中」はまだ分かっていない値です。</p>\n'
         "  <script>(function(){var n=Date.now();document.querySelectorAll('.c4-rc[data-end]').forEach(function(x){"
         "if(n>=Date.parse(x.getAttribute('data-end')))x.parentNode.removeChild(x)})})();</script>")

page = here / "src/pages/pawaque-saikyuki-coach4.html"
s = page.read_text(encoding="utf-8")
s = re.sub(r"<!-- C4:START -->.*?<!-- C4:END -->", lambda m: "<!-- C4:START -->\n" + body + "\n  <!-- C4:END -->", s, flags=re.S)
page.write_text(s, encoding="utf-8")
print("ok coach4", len(A), "人（4）", len(B), "人（5）")
