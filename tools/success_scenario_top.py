"""サクセスの新シナリオのトップ（src/pages/success-<キー>.html）と子ページの「カード型リンク欄」を作る。
西球記（tools/pawaque_saikyuki_top.py）と同じ形（2026-11-20 管理人「パワクエ西球記のような形」）。
設定は src/success_data/<ファイル>.json（名前・配信日・子ページ）。値は管理人が教えてくれたものだけを入れる（推測で書かない）。
使い方： python3 tools/success_scenario_top.py [src/success_data/new_scenario.json] → python3 build.py
- 子ページの「準備OK」が false のカードは出さない（中身が入ったら true に。そのページの noindex: yes も消す）。
- おすすめデッキ（decks/<キー>/）とイベキャラランキング（ranking/<キー>/）は、ロマン開花・アンドロメダと同じ仕組みのページにリンクする。
- ページの先頭に sk_updated: YYYY-MM-DD を書くと、カードに緑太字「※○/○更新!」が出て7日後14時に消える（西球記と同じ）。
- カードの文字の途中で折り返したくない時は「表示名」に HTML（cp-nw の span）で書く。
- json の「概要」（実装日・空きイベント数・金特・所持経験点上限・所属キャラ）から、トップの <!-- SCABOUT:START/END --> に概要の表を作る。空欄は「調査中」。
- ページの <!-- SCTOP:START/END -->（トップ）と <!-- SKNAV:START/END -->（子ページ）の間を書き換える。"""
import datetime as _dt, html, json, re, sys
from pathlib import Path

here = Path(__file__).resolve().parent.parent
e = html.escape
cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "src/success_data/new_scenario.json"
C = json.loads(cfg_path.read_text(encoding="utf-8"))
KEY = C["キー"]
NAME = C["名前"] or "新シナリオ"
page = here / f"src/pages/success-{KEY}.html"

JST = _dt.timezone(_dt.timedelta(hours=9))
UPD = {}
for _f in (here / "src/pages").glob("*.html"):
    _h = _f.read_text(encoding="utf-8")[:1500]
    _p = re.search(r"^path: *(\S+)", _h, re.M)
    _u = re.search(r"^sk_updated: *(\d{4}-\d{2}-\d{2})", _h, re.M)
    if _p and _u:
        UPD[_p.group(1)] = _u.group(1)


def upd_tag(href):
    d = UPD.get(href)
    if not d:
        return ""
    day = _dt.date.fromisoformat(d)
    end = _dt.datetime.combine(day + _dt.timedelta(days=7), _dt.time(14, 0), JST)
    if _dt.datetime.now(JST) >= end:
        return ""
    return f'<span class="sk-upd" data-end="{end.isoformat()}">※{day.month}/{day.day}更新!</span>'


UPD_JS = ("  <script>(function(){var n=Date.now();document.querySelectorAll('.sk-upd[data-end]').forEach(function(e){"
          "if(n>=Date.parse(e.getAttribute('data-end')))e.parentNode.removeChild(e)})})();</script>")


def href_of(c):
    if c.get("リンク"):   # http で始まるものはサイトの外（例：ロマン開花のコスト計算ツール）   # 既にあるページへのリンク（例：有能キャラ予想 ranking/next_batter/、2026-11-22 管理人）
        return c["リンク"]
    if c["キー"] == "decks":
        return f"decks/{KEY}/"
    if c["キー"] == "ranking":
        return f"ranking/{KEY}/"
    return f"success/{KEY}/{c['キー']}/"


CUR = None


def card(c):
    if not c.get("準備OK"):
        if c.get("準備中で出す"):   # リンクは貼らず、タイトルと（準備中）だけ出す（2026-11-22 管理人）
            th = '<span class="sk-th">画像準備中</span>'
            return (f'    <span class="sk-c sk-off">{th}<span class="sk-l">{c.get("表示名") or e(c["名前"])}</span>'
                    f'<span class="sk-wait">準備中</span></span>')
        return None
    href = href_of(c)
    img = c.get("画像") or C.get("ロゴ画像")
    th = (f'<span class="sk-th sk-img"><img src="{{{{root}}}}{e(img)}" alt="{e(c["名前"])}" loading="lazy"></span>' if img
          else '<span class="sk-th">画像準備中</span>')
    th += f'<span class="sk-l">{c.get("表示名") or e(c["名前"])}</span>{upd_tag(href)}<span class="sk-s">{c.get("説明", "")}</span>'
    if href == CUR:
        return f'    <span class="sk-c sk-cur" aria-current="page">{th}<span class="sk-now">表示中のページ</span></span>'
    if href.startswith("http"):
        return f'    <a class="sk-c" href="{e(href)}" target="_blank" rel="noopener">{th}</a>'
    return f'    <a class="sk-c" href="{{{{root}}}}{href}">{th}</a>'


def grid(cs):
    """スマホは横3列・PCなど広い画面は横4列（2026-11-22 管理人）。空きマスは白で埋める"""
    n = len(cs)
    mob, pcf = (3 - n % 3) % 3, (4 - n % 4) % 4   # スマホ3列・PC4列で最後の行の空き
    fill = []
    for i in range(max(mob, pcf)):
        cls = "sk-fill" + ("" if i < mob and i < pcf else (" sk-fill-sp" if i < mob else " sk-fill-pc"))
        fill.append(f'    <span class="{cls}" aria-hidden="true"></span>')
    return ['  <div class="sk-grid sk-sp3">'] + cs + fill + ['  </div>']


def nav(bottom=False):
    cs = [x for x in (card(c) for c in C["子ページ"]) if x]
    if not cs:
        return '  <p class="muted">攻略ページは配信後に順に追加します。</p>' if not bottom else ""
    cls = "sk-nav sk-nav-btm" if bottom else "sk-nav"
    return "\n".join([f'  <section class="{cls}" aria-label="{e(NAME)}の関連ページ">',
                      f'  <p class="sk-nav-h">{e(NAME)}の攻略ページ</p>'] + grid(cs) + [UPD_JS, '  </section>'])


# シナリオの概要の表（2026-11-24 管理人のテンプレ）。json の「概要」から <!-- SCABOUT:START/END --> の間を作る。
# 空欄は「調査中」。空きイベント数は 前＝黄色太字・後＝濃い青太字。金特は投手・野手で行を分ける。
def about_table():
    A = C.get("概要")
    if A is None:
        return None
    wait = '<span class="sa-wait">調査中</span>'
    def val(v):
        return e(str(v)) if str(v).strip() else wait
    def items(v):
        v = [x for x in (v or []) if str(x).strip()]
        if not v:
            return wait
        return '<span class="sa-list">' + "".join(f'<span class="sa-i">{e(str(x))}</span>' for x in v) + "</span>"
    mae, ato = val(A.get("空きイベント数_前", "")), val(A.get("空きイベント数_後", ""))
    _n = empty_counts()
    if _n is not None:
        mae, ato = str(_n["前"]), str(_n["後"])
    rows = [
        ("実装日", val(A.get("実装日", ""))),
        ("空き<span class=\"cp-nw\">イベント数</span>", f'<span class="sa-ev"><span class="cp-nw sa-mae">前：<b>{mae}</b></span>'
                           f'<span class="cp-nw sa-ato">後：<b>{ato}</b></span></span>'),
    ]
    out = ['  <table class="sa-t">', "  <tbody>"]
    for th, td in rows:
        out.append(f"    <tr><th>{th}</th><td>{td}</td></tr>")
    out.append(f'    <tr><th rowspan="2">取得可能な<span class="cp-nw">金特</span></th>'
               f'<td><span class="sa-pos sa-pos-p">投手</span>{items(A.get("金特_投手"))}</td></tr>')
    out.append(f'    <tr><td><span class="sa-pos">野手</span>{items(A.get("金特_野手"))}</td></tr>')
    out.append(f'    <tr><th>所持経験点<span class="cp-nw">上限</span></th><td>{val(A.get("所持経験点上限", ""))}</td></tr>')
    out.append(f'    <tr><th>シナリオ<span class="cp-nw">所属キャラ</span></th><td>{items(A.get("所属キャラ"))}</td></tr>')
    out += ["  </tbody>", "  </table>"]
    return "\n".join(out)


# 固有イベントの表（2026-11-24 管理人の画像の形）。json の「固有イベント」から <!-- SCEVENT:START/END --> の間を作る。
# セクションごとに「週・前・後」の表。イベントのある欄は 前＝薄い黄色・後＝薄い青の背景。詳細は {青:…}{緑:…}{赤:…} で色。
_TXC = {"青": "tx-b", "緑": "tx-g", "赤": "tx-r", "青太": "tx-b tx-bold", "緑太": "tx-g tx-bold", "赤太": "tx-r tx-bold", "太": "tx-bold"}
def _deco(x):
    x = e(str(x))
    return re.sub(r"[{｛](青太|緑太|赤太|青|緑|赤|太)[:：](.*?)[}｝]", lambda m: f'<span class="{_TXC[m.group(1)]}">{m.group(2)}</span>', x)

def event_tables():
    V = C.get("固有イベント")
    if V is None:
        return None
    WS = V.get("週", {})
    out = []
    for sec in V["セクション"]:
        W = WS.get(sec["名前"], {})  # 週はセクションごと（8月1〜3週がセクション1と4にあるため）
        out.append(f'  <h3 class="se-h">{e(sec["名前"])}<span class="se-r">（{e(sec["週"][0])}〜{e(sec["週"][-1])}）</span></h3>')
        out.append('  <table class="se-t">')
        out.append('  <thead><tr><th class="se-w"></th><th class="se-mae">前</th><th class="se-ato">後</th></tr></thead>')
        out.append("  <tbody>")
        for wk in sec["週"]:
            cells = []
            for side, cls in (("前", "se-on-mae"), ("後", "se-on-ato")):
                evs = (W.get(wk) or {}).get(side) or []
                if not evs:  # 「色を塗る空欄」に書いた所は、空でも背景色を付ける
                    paint = side in V.get("色を塗る空欄", {}).get(sec["名前"], {}).get(wk, [])
                    cells.append(f'<td class="{cls}"></td>' if paint else "<td></td>")
                    continue
                body = "".join(f'<div class="se-ev"><b>{_deco(v["名前"])}</b>'
                               + "".join(f"<span>{_deco(x)}</span>" for x in v.get("詳細", [])) + "</div>" for v in evs)
                cells.append(f'<td class="{cls}">{body}</td>' if _colored(evs) else f"<td>{body}</td>")
            out.append(f'    <tr><th class="se-w">{e(wk)}</th>{"".join(cells)}</tr>')
        out += ["  </tbody>", "  </table>"]
    return "\n".join(out)



def _colored(evs):
    """セルに色を付けるか。イベント名を () か （） で囲んだものは「空きイベント扱い」で色を付けない（2026-11-24 管理人）"""
    return any(not re.match(r"^\s*[（(].*[）)]\s*$", str(v.get("名前", ""))) for v in (evs or []))

def empty_counts():
    """空きイベント数（前・後）。固有イベントの表で、色の付いていないセル（イベント無し、または名前を()で囲んだ空き扱いのイベント）を前・後ごとに数える。「数えない週」は除く"""
    V = C.get("固有イベント") or {}
    if not V.get("空きイベント数を数える"):
        return None
    WS, skip = V.get("週", {}), V.get("数えない週", {})
    n = {"前": 0, "後": 0}
    for sec in V["セクション"]:
        W = WS.get(sec["名前"], {})
        for wk in sec["週"]:
            if wk in skip.get(sec["名前"], []):
                continue
            for side in n:
                if not _colored((W.get(wk) or {}).get(side)):  # 色の付いていないセルを数える
                    n[side] += 1
    return n


# ランダムイベント（2026-11-24 管理人「イベキャラのイベント表の形を流用」）。charpages.py の event_detail で作る。
# 「前」「後」に分けて出す。並びは _rank の順（同じ順位は書いた順、2026-11-25 管理人）。
def _rows(x):
    rows = list(x.get("行", []))
    for s in x.get("小イベント", []):
        rows += s.get("行", [])
    return rows

def _rank(x):
    """並び順（2026-11-25 管理人）：1 体力+ → 2 体力最大値+ → 3 いいヤツ・世渡り上手・モテモテ → 4 やる気+ → 5 コツLv → 6 ○○評価+ → 7 なにもなし"""
    items = [str(i) for r in _rows(x) for k, v in r.items() if isinstance(v, list) for i in v]
    tests = (lambda i: re.match(r"^体力[+＋]", i),
             lambda i: re.match(r"^体力最大値[+＋]", i),
             lambda i: re.match(r"^(いいヤツ|世渡り上手|モテモテ)", i),
             lambda i: re.match(r"^やる気[+＋]", i),
             lambda i: "コツLv" in i,
             lambda i: re.search(r"評価[+＋]", i))
    for n, f in enumerate(tests):
        if any(f(i) for i in items):
            return n
    return len(tests)


def random_events():
    V = C.get("ランダムイベント")
    if V is None:
        return None
    sys.path.insert(0, str(here))
    import charpages as cp
    cp._CTYPE[0] = {"投手": "投手用", "野手": "野手用"}.get(C.get("種別", ""))
    out = []
    for side in ("前", "後"):
        evs = sorted(V.get(side, []), key=_rank)
        out.append(f'  <h3 class="se-h">{side}イベント</h3>')
        if not evs:
            out.append('  <p class="muted">準備中です。</p>')
            continue
        ev = {}
        for x in evs:
            y = {k: v for k, v in x.items() if k not in ("名前", "行")}
            if x.get("行"):
                y["小イベント"] = [{"行": x["行"]}] + y.get("小イベント", [])
            ev[x["名前"]] = y
        out.append(f'  <section class="cp-sec sc-rnd">{cp.event_detail(ev)}</section>')
    return "\n".join(out)

# トップ
s = page.read_text(encoding="utf-8")
assert "<!-- SCTOP:START -->" in s and "<!-- SCTOP:END -->" in s, "SCTOP の目印が見つからない"
s = re.sub(r"(<!-- SCTOP:START -->).*?(<!-- SCTOP:END -->)", lambda m: m.group(1) + "\n" + nav() + "\n  " + m.group(2), s, flags=re.S)
_ab = about_table()
if _ab is not None:
    assert "<!-- SCABOUT:START -->" in s, "SCABOUT の目印が見つからない"
    s = re.sub(r"(<!-- SCABOUT:START -->).*?(<!-- SCABOUT:END -->)", lambda m: m.group(1) + "\n" + _ab + "\n  " + m.group(2), s, flags=re.S)
_ev = event_tables()
if _ev is not None:
    assert "<!-- SCEVENT:START -->" in s, "SCEVENT の目印が見つからない"
    s = re.sub(r"(<!-- SCEVENT:START -->).*?(<!-- SCEVENT:END -->)", lambda m: m.group(1) + "\n" + _ev + "\n  " + m.group(2), s, flags=re.S)
_rn = random_events()
if _rn is not None:
    assert "<!-- SCRANDOM:START -->" in s, "SCRANDOM の目印が見つからない"
    s = re.sub(r"(<!-- SCRANDOM:START -->).*?(<!-- SCRANDOM:END -->)", lambda m: m.group(1) + "\n" + _rn + "\n  " + m.group(2), s, flags=re.S)
page.write_text(s, encoding="utf-8")
print("ok トップ", NAME, sum(1 for c in C["子ページ"] if c.get("準備OK")), "枚")

# 子ページ（src/pages/success-<キー>-*.html）の一番下
for f in sorted((here / "src/pages").glob(f"success-{KEY}-*.html")):
    CUR = f"success/{KEY}/{f.stem.removeprefix(f'success-{KEY}-')}/"
    t = f.read_text(encoding="utf-8")
    assert "<!-- SKNAV:START -->" in t, f"{f.name}: SKNAV の目印が見つからない"
    t = re.sub(r"(<!-- SKNAV:START -->).*?(<!-- SKNAV:END -->)", lambda m: m.group(1) + "\n" + nav(True) + "\n  " + m.group(2), t, flags=re.S)
    f.write_text(t, encoding="utf-8")
# 既にある別の場所のページ（例：ロマン開花の decks/roman/・deckbuild/roman/）にも一番下のリンク欄を付ける。
# json の「リンク欄を付けるページ」に src/pages のファイル名を書く。ページに <!-- SKNAV:START/END --> の目印を置いておく。
for fn in C.get("リンク欄を付けるページ", []):
    f = here / "src/pages" / fn
    t = f.read_text(encoding="utf-8")
    CUR = re.search(r"^path: *(\S+)", t, re.M).group(1)
    assert "<!-- SKNAV:START -->" in t, f"{fn}: SKNAV の目印が見つからない"
    t = re.sub(r"(<!-- SKNAV:START -->).*?(<!-- SKNAV:END -->)", lambda m: m.group(1) + "\n" + nav(True) + "\n  " + m.group(2), t, flags=re.S)
    f.write_text(t, encoding="utf-8")
    print("ok リンク欄", fn)
# ランキングページ（charpages.py が ranking.json から作る）用は src/success_data/sknav_<ランキングのキー>.html に書き出し、charpages.py が一番下に付ける
for rk in C.get("リンク欄を付けるランキング", []):
    CUR = f"ranking/{rk}/"
    (here / f"src/success_data/sknav_{rk}.html").write_text(nav(True) + "\n", encoding="utf-8")
    print("ok ランキングのリンク欄", rk)
CUR = None
print("ok 子ページのリンク欄", len(list((here / "src/pages").glob(f"success-{KEY}-*.html"))), "ページ")
