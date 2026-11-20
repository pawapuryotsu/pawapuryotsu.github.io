"""サクセスの新シナリオのトップ（src/pages/success-<キー>.html）と子ページの「カード型リンク欄」を作る。
西球記（tools/pawaque_saikyuki_top.py）と同じ形（2026-11-20 管理人「パワクエ西球記のような形」）。
設定は src/success_data/<ファイル>.json（名前・配信日・子ページ）。値は管理人が教えてくれたものだけを入れる（推測で書かない）。
使い方： python3 tools/success_scenario_top.py [src/success_data/new_scenario.json] → python3 build.py
- 子ページの「準備OK」が false のカードは出さない（中身が入ったら true に。そのページの noindex: yes も消す）。
- おすすめデッキ（decks/<キー>/）とイベキャラランキング（ranking/<キー>/）は、ロマン開花・アンドロメダと同じ仕組みのページにリンクする。
- ページの先頭に sk_updated: YYYY-MM-DD を書くと、カードに緑太字「※○/○更新!」が出て7日後14時に消える（西球記と同じ）。
- カードの文字の途中で折り返したくない時は「表示名」に HTML（cp-nw の span）で書く。
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
    if c["キー"] == "decks":
        return f"decks/{KEY}/"
    if c["キー"] == "ranking":
        return f"ranking/{KEY}/"
    return f"success/{KEY}/{c['キー']}/"


CUR = None


def card(c):
    if not c.get("準備OK"):
        return None
    href = href_of(c)
    img = c.get("画像") or C.get("ロゴ画像")
    th = (f'<span class="sk-th sk-img"><img src="{{{{root}}}}{e(img)}" alt="{e(c["名前"])}" loading="lazy"></span>' if img
          else '<span class="sk-th">画像準備中</span>')
    th += f'<span class="sk-l">{c.get("表示名") or e(c["名前"])}</span>{upd_tag(href)}<span class="sk-s">{c.get("説明", "")}</span>'
    if href == CUR:
        return f'    <span class="sk-c sk-cur" aria-current="page">{th}<span class="sk-now">表示中のページ</span></span>'
    return f'    <a class="sk-c" href="{{{{root}}}}{href}">{th}</a>'


def grid(cs):
    """西球記と同じ並び（スマホ2列・PC3列、空きマスは白で埋める）"""
    n = len(cs)
    g, pc = "sk-grid", 3
    if n % 3 and n % 2 == 0:
        pc = n if n <= 4 else 2
        g += f" sk-g{pc}"
    mob, pcf = (2 - n % 2) % 2, (pc - n % pc) % pc
    fill = []
    for i in range(max(mob, pcf)):
        cls = "sk-fill" + ("" if i < mob and i < pcf else (" sk-fill-sp" if i < mob else " sk-fill-pc"))
        fill.append(f'    <span class="{cls}" aria-hidden="true"></span>')
    return [f'  <div class="{g}">'] + cs + fill + ['  </div>']


def nav(bottom=False):
    cs = [x for x in (card(c) for c in C["子ページ"]) if x]
    if not cs:
        return '  <p class="muted">攻略ページは配信後に順に追加します。</p>' if not bottom else ""
    cls = "sk-nav sk-nav-btm" if bottom else "sk-nav"
    return "\n".join([f'  <section class="{cls}" aria-label="{e(NAME)}の関連ページ">',
                      f'  <p class="sk-nav-h">{e(NAME)}の攻略ページ</p>'] + grid(cs) + [UPD_JS, '  </section>'])


# トップ
s = page.read_text(encoding="utf-8")
assert "<!-- SCTOP:START -->" in s and "<!-- SCTOP:END -->" in s, "SCTOP の目印が見つからない"
s = re.sub(r"(<!-- SCTOP:START -->).*?(<!-- SCTOP:END -->)", lambda m: m.group(1) + "\n" + nav() + "\n  " + m.group(2), s, flags=re.S)
page.write_text(s, encoding="utf-8")
print("ok トップ", NAME, sum(1 for c in C["子ページ"] if c.get("準備OK")), "枚")

# 子ページ（src/pages/success-<キー>-*.html）の一番下
for f in sorted((here / "src/pages").glob(f"success-{KEY}-*.html")):
    CUR = f"success/{KEY}/{f.stem.removeprefix(f'success-{KEY}-')}/"
    t = f.read_text(encoding="utf-8")
    assert "<!-- SKNAV:START -->" in t, f"{f.name}: SKNAV の目印が見つからない"
    t = re.sub(r"(<!-- SKNAV:START -->).*?(<!-- SKNAV:END -->)", lambda m: m.group(1) + "\n" + nav(True) + "\n  " + m.group(2), t, flags=re.S)
    f.write_text(t, encoding="utf-8")
CUR = None
print("ok 子ページのリンク欄", len(list((here / "src/pages").glob(f"success-{KEY}-*.html"))), "ページ")
