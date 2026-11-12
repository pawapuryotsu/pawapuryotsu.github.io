# パワプロアプリ攻略ベース：src/ の部品から公開用の docs/ を作る
#   python3 build.py [chars.json の場所]
# chars.json を省くと ../pawa-data/event-chars/chars.json を使う。
import json, pathlib, re, shutil, sys
from datetime import date

# ===== 設定（ここだけ書き換えればOK） =====
SITE_URL = "https://pawapuryotsu.com"   # 独自ドメインにしたら "https://example.com" のように変える
CUSTOM_DOMAIN = "pawapuryotsu.com"                          # 独自ドメインを使うときだけ "example.com" と書く（CNAME ファイルになる）
ADSENSE_CLIENT = "ca-pub-8546020269968696"                           # AdSense のサイト追加で出る "ca-pub-1234567890123456"
AD_SLOT = ""                                  # 広告ユニット（ディスプレイ広告）を作ったらその番号。空なら広告枠は出さない
OPERATOR = "りょーつー"                       # 運営者名（ハンドルネーム）。ハンドルネーム以外は書かない
OPERATOR_INTRO = "パワプロアプリをプレイしながら、YouTube でデッキ解説や育成動画を投稿しています。"
CONTACT_FORM = "https://forms.gle/mXyapp3TYUPzyLAz6"                             # Googleフォームの URL（https://forms.gle/...）
GA_ID = "G-F98XGNW3LS"                                    # Googleアナリティクス4の測定ID（G-XXXXXXXXXX）。空なら解析なし
POLICY_DATE = "2026年10月"                    # プライバシーポリシーの制定日

NAV = [("home", "", "トップ"), ("roman", "decks/roman/", "ロマン開花學園<small>投手</small>"),
       ("andromeda", "decks/andromeda/", "アンドロメダ学園<small>野手</small>"), ("pawaque", "pawaque/contract_simulator/", "パワクエ"), ("about", "about/", "このサイトについて")]

here = pathlib.Path(__file__).parent
src, out = here / "src", here / "docs"
chars = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else here.parent / "pawa-data" / "event-chars" / "chars.json"
pub = ADSENSE_CLIENT.replace("ca-", "")


def adsense_head():
    if not ADSENSE_CLIENT:
        return ""
    return (f'<meta name="google-adsense-account" content="{ADSENSE_CLIENT}">\n'
            f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>')


def ad_block():
    if not (ADSENSE_CLIENT and AD_SLOT):
        return ""
    return (f'<div class="ad-slot"><ins class="adsbygoogle" style="display:block" data-ad-client="{ADSENSE_CLIENT}" '
            f'data-ad-slot="{AD_SLOT}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
            '<script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></div>')


def ga_head():
    if not GA_ID:
        return ""
    return (f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>\n'
            f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{GA_ID}');</script>")


def analytics_note():
    if not GA_ID:
        return "当サイトは現在、アクセス解析ツール（Google アナリティクスなど）を使っていません。導入する場合はこのページでお知らせします。"
    return ("当サイトは、アクセス状況を把握するために Google アナリティクス（GA4）を使っています。Google アナリティクスは Cookie を使って、個人を特定しない形でアクセス情報（閲覧ページ、おおよその地域、使用端末など）を収集します。"
            "収集を望まない場合は、ブラウザの設定で Cookie を無効にするか、<a href=\"https://tools.google.com/dlpage/gaoptout\" target=\"_blank\" rel=\"noopener\">Google アナリティクス オプトアウト アドオン</a>を利用してください。"
            "詳しくは <a href=\"https://policies.google.com/technologies/partner-sites?hl=ja\" target=\"_blank\" rel=\"noopener\">Google のポリシー</a>をご覧ください。")


def contact_block():
    if CONTACT_FORM:
        return f'<p><a class="btn" style="background:var(--field);color:var(--field-ink)" href="{CONTACT_FORM}" target="_blank" rel="noopener">お問い合わせフォームを開く</a></p>'
    return ""


# サイトマップの lastmod 用：作り直す前の各ページの中身と更新日を覚えておく（中身が変わったページだけ今日の日付にする）
_VER_RE = re.compile(r"\?v=[0-9a-f]{8}")
_DATE_RE = re.compile(r'<p class="pubdate">.*?</p>\n?|<script type="application/ld\+json">\{"@context": "https://schema.org", "@type": "Article".*?</script>\n?|<!--recent-->.*?<!--/recent-->', re.S)
def _norm(html):
    """前回と中身を比べるとき、?v= の番号・公開日/更新日の行・トップの「最近の更新」欄は除いて比べる"""
    return _DATE_RE.sub("", _VER_RE.sub("", html))
_old_lastmod, _old_html = {}, {}
if (out / "sitemap.xml").exists():
    _old_lastmod = dict(re.findall(r"<loc>(.*?)</loc><lastmod>(.*?)</lastmod>", (out / "sitemap.xml").read_text(encoding="utf-8")))
    for _f in out.rglob("index.html"):
        _old_html[_f.relative_to(out).as_posix()] = _norm(_f.read_text(encoding="utf-8"))
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src / "assets", out / "assets")
shutil.copytree(src / "img", out / "img")
(out / "data").mkdir()
# 公開する chars.json（デッキページ用）にはキャラページ専用の「プロフィール」を入れない（ファイルを軽く保つため）
_pub = [{k: v for k, v in c.items() if k != "プロフィール"} for c in json.loads(chars.read_text(encoding="utf-8"))]
(out / "data" / "chars.json").write_text(json.dumps(_pub, ensure_ascii=False, indent=1), encoding="utf-8")
shutil.copy(src / "decks.js", out / "assets" / "decks.js")
# Tier表メーカー（pawa-data の tools/build_tier_maker.py --site で src/tier/ に作る。ページ本体とアイコン画像）
if (src / "tier").exists():
    shutil.copytree(src / "tier", out / "tier")
    # layout.html を通らない単体ページにも、解析（GA4）のコードを入れる。
    # ツール単体ページには AdSense のコードを入れない（審査で「文章のないページに広告」と見られないため。2026-11-03 りょーつー指示）
    for page in (out / "tier").glob("*.html"):
        html = page.read_text(encoding="utf-8")
        if "googletagmanager" not in html:
            page.write_text(html.replace("</head>", ga_head() + "\n</head>", 1), encoding="utf-8")
# パワクエのページ（src/pawaque/ の下。契約書シミュレータは pawa-data の powaque/simulator/build_site.py で src/pawaque/contract_simulator/ に作る。1枚のHTML）
if (src / "pawaque").exists():
    shutil.copytree(src / "pawaque", out / "pawaque")
    for page in (out / "pawaque").rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        if "googletagmanager" not in html:
            page.write_text(html.replace("</head>", ga_head() + "\n</head>", 1), encoding="utf-8")
    # 契約書シミュレータを軽くする（2026-11-12 管理人OK）：厳密計算の部品（HiGHS、約1.8MB）を highs.js に分けて、
    # 厳密計算を始めたときだけ読み込む。最初に開くときはこの分を読まない（見た目・計算結果は同じ）
    import hashlib
    sim = out / "pawaque" / "contract_simulator" / "index.html"
    if sim.exists():
        html = sim.read_text(encoding="utf-8")
        m = re.search(r"<script>(const HIGHS_SRC = .*?)</script>\n?", html, re.S)
        hook = "    ready = (async () => {\n"
        if m and html.count(hook) == 1:
            js = m.group(1)
            (sim.parent / "highs.js").write_text(js, encoding="utf-8")
            v = hashlib.md5(js.encode()).hexdigest()[:8]
            load = (f'      if (typeof HIGHS_SRC === "undefined") await new Promise((ok, ng) => {{ const sc = document.createElement("script"); '
                    f'sc.src = "highs.js?v={v}"; sc.onload = ok; sc.onerror = () => ng(new Error("厳密計算の部品を読み込めませんでした")); document.head.appendChild(sc); }});\n')
            html = (html[:m.start()] + html[m.end():]).replace(hook, hook + load, 1)
            sim.write_text(html, encoding="utf-8")
# 古いCSS/JSがスマホに残らないよう、ファイルの中身から作った番号を ?v= で付ける
import hashlib
ver = {f: hashlib.md5((out / "assets" / f).read_bytes()).hexdigest()[:8] for f in ("style.css", "deck.js", "decks.js", "gacha.js")}

# サイトマップの lastmod は「本当に更新した日」だけ書く（毎回今日の日付だとGoogleに無視される）。
# デッキページ＝そのシナリオのデッキの一番新しい育成日。それ以外のページは書かない。
decks_js = (src / "decks.js").read_text(encoding="utf-8")
deck_dates = {}
for school, block in re.findall(r"^  (\w+):\{title:(.*?)(?=^  \w+:\{title:|\Z)", decks_js, re.S | re.M):
    d = re.findall(r'date:"(\d{4}-\d{2}-\d{2})"', block)
    if d:
        deck_dates[school] = max(d)

# デッキページの文章（デッキ名簿・育成のポイント）を、JavaScript なしでも読めるHTMLとして先に埋め込む。
# 検索エンジンや広告審査のロボットは JS を実行しないことがあり、「読み込み中…」だけに見えてしまうため。
# ブラウザでは deck.js が #deckapp を同じ内容の見やすい表示に置き換える。
import html as _html, json as _json, subprocess
_dump = subprocess.run(["node", "-e", "global.window={};require(process.argv[1]);console.log(JSON.stringify(window.DECKS))", str(src / "decks.js")],
                       capture_output=True, text=True, check=True).stdout
DECKS = _json.loads(_dump)
_e = _html.escape


def char_link(n):
    """デッキのキャラ名。キャラページがあればリンクにする（SEOの内部リンク。2026-11-12 管理人OK）"""
    p = charpages.CHAR_PATHS.get(n)
    return f'<a href="{{{{root}}}}{p}">{_e(n)}</a>' if p else _e(n)


def static_decks(school):
    d = DECKS[school]
    parts = [f'<div class="static-decks"><p>{_e(d["title"])}（{_e(d["kind"])}）で実際に育成したデッキの一覧です。</p>']
    for i, k in enumerate(d["list"], 1):
        mains = "、".join(f'{char_link(n)}（{_e(r)} Lv{lv}）' for n, r, lv, *_ in k["main"])
        subs = "、".join(f'{char_link(n)}（{_e(r)} Lv{lv}）' for n, r, lv, *_ in k["sub"])
        f2p = "・無課金" if k.get("f2p") else ""
        parts.append(f'<h2>デッキ{i}：{_e(k["pos"])}・選手ランク{k["rank"]}{f2p}・総経験点 {k["exp"]:,}</h2>'
                     f'<p>育成日：{_e(k["date"])}</p><p>メインデッキ：{mains}</p><p>サポートデッキ：{subs}</p>')
        if k.get("tips"):
            parts.append("<h3>育成のポイント</h3><ul>" + "".join(f"<li>{_e(t)}</li>" for t in k["tips"]) + "</ul>")
        if k.get("memo"):
            parts.append("<h3>育成メモ</h3><ul>" + "".join(f"<li>{_e(t)}</li>" for t in k["memo"]) + "</ul>")
    parts.append("</div>")
    return "\n".join(parts)


layout = (src / "layout.html").read_text(encoding="utf-8")
urls = []
import charpages
_char_pages = charpages.generate(chars, src, DECKS)  # キャラページ（評価を書くまでは noindex）
import gachapages
_gacha_pages, _gacha_cards = gachapages.generate(src)  # ガチャ記事（src/gacha/*.json）とトップの「ガチャ」欄のカード
(out / "img" / "chars").mkdir(exist_ok=True)
for _f, _dst in charpages.ICON_COPIES:                # 一覧に出すキャラのアイコン（130x130）
    shutil.copy(_f, out / _dst)
_all_pages = [p.read_text(encoding="utf-8") for p in sorted((src / "pages").glob("*.html"))] + _char_pages + _gacha_pages
_parsed = []
for text in _all_pages:
    meta_txt, body = re.match(r"<!--(.*?)-->\n(.*)", text, re.S).groups()
    _parsed.append((dict(re.findall(r"^(\w+):[ \t]*(.*)$", meta_txt, re.M)), body))
# パンくずリスト：ページの名前（meta の crumb、無ければ title の「｜」より前）。上の階層のページがあればそこを通る（無い階層は飛ばす）
CRUMB = {m["path"]: m.get("crumb") or m["title"].split("｜")[0] for m, _ in _parsed}


def crumbs(path):
    if path in ("", "404.html"):
        return []
    parts = path.strip("/").split("/")
    chain = [("", "トップ")] + [(p, CRUMB[p]) for p in ("/".join(parts[:i]) + "/" for i in range(1, len(parts))) if p in CRUMB]
    return chain + [(path, CRUMB[path])]


def crumb_html(chain):
    _e2 = _html.escape
    li = "".join(f'<li><a href="{{{{root}}}}{p}">{_e2(n)}</a></li>' for p, n in chain[:-1]) + f'<li aria-current="page">{_e2(chain[-1][1])}</li>'
    return f'<nav class="crumbs" aria-label="パンくずリスト"><ol>{li}</ol></nav>\n'


def crumb_ld(chain):
    return json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": f"{SITE_URL}/{p}"} for i, (p, n) in enumerate(chain, 1)]}, ensure_ascii=False)


# SNSで共有したときの画像（og:image）。ページごとに docs/img/og/ に自動で作る（2026-11-12 管理人OK）
import ogimage
OG_LABEL = [("chars/", "イベキャラ"), ("gacha/", "ガチャ"), ("ranking/", "ランキング"), ("decks/", "デッキまとめ"),
            ("deckbuild/", "デッキの組み方"), ("guide/", "ガイド")]


def og_image(meta, path):
    if path == "404.html":
        return ""
    slug = path.strip("/").replace("/", "_") or "top"
    if path == "":
        title, label = "パワプロアプリ ガチ勢による最先端攻略サイト", ""
    else:
        title = meta.get("og_title") or (meta.get("crumb") if "{{" in meta["title"] else None) or meta["title"].split("｜")[0]
        label = next((l for pre, l in OG_LABEL if path.startswith(pre)), "")
    icon = meta.get("og_icon") or (f"img/chars/{path.split('/')[1]}.png" if re.fullmatch(r"chars/\d{4}/", path) else None)
    icon = out / icon if icon and (out / icon).exists() else None
    ogimage.make(out / "img" / "og" / f"{slug}.png", title, label, icon)
    u = f"{SITE_URL}/img/og/{slug}.png"
    return (f'<meta property="og:image" content="{u}">\n<meta property="og:image:width" content="1200">\n'
            f'<meta property="og:image:height" content="630">\n<meta name="twitter:image" content="{u}">')


import subprocess as _sp
REDIRECT_FROM = {"guide/how_to_read/": "guide/how-to-read/", "guide/cost_tool/": "guide/cost-tool/", "ranking/next_batter/": "ranking/next-batter/"}


def first_published(path):
    """公開日＝そのページ（URLを変えたページは古いURLも）を最初にコミットした日。まだコミットしていない新しいページは今日"""
    ds = []
    for p in filter(None, (path, REDIRECT_FROM.get(path))):
        r = _sp.run(["git", "log", "--diff-filter=A", "--format=%cs", "--", f"docs/{p}index.html"], cwd=here, capture_output=True, text=True).stdout.split()
        ds += r
    return min(ds) if ds else date.today().isoformat()


def ymd(d):
    return d.replace("-", "/")


# 公開日・更新日を出す記事（ページの見出しの下に表示＋Article の構造化データ。2026-11-12 管理人OK）
DATED = ("gacha/", "ranking/")
# トップの「最近の更新」欄（2026-11-12 管理人OK）。src/home_updates.json の「トップに出さないページ」に書いたページは出さない
_hu = json.loads((src / "home_updates.json").read_text(encoding="utf-8")) if (src / "home_updates.json").exists() else {}
HOME_SKIP = set(_hu.get("トップに出さないページ", [])) | {"", "404.html", "about/", "privacy/", "contact/"}
HOME_N = int(_hu.get("出す件数", 8))
_page_info = []   # (path, 名前, 更新日, 公開日, 種類, アイコン)


def _nice_break(name):
    """「…のガチャは引くべき？」「…のイベント・評価」の後ろ半分は途中で折り返さない（スマホで「あか／ねの」のように切れないように）"""
    m = re.match(r"(.*)(の(?:ガチャは引くべき？|イベント・評価|イベント))$", name)
    if not m:
        return _html.escape(name)
    return f'{_html.escape(m.group(1))}<wbr><span class="cp-nw">{_html.escape(m.group(2))}</span>'


def recent_html():
    items = sorted((x for x in _page_info if x[0] not in HOME_SKIP), key=lambda x: (x[2] or "", x[3] or "", x[0]), reverse=True)[:HOME_N]
    li = []
    for path, name, lm, pub, label, icon in items:
        img = f'<img class="news-icon" src="{{{{root}}}}{icon}" alt="" width="44" height="44" loading="lazy">' if icon else ""
        li.append(f'<li{"" if icon else " class=rc-noimg"}><a href="{{{{root}}}}{path}">{img}<span><small class="rc-meta">{ymd(lm)} 更新{"・" + _html.escape(label) if label else ""}</small><b>{_nice_break(name)}</b></span></a></li>')
    return "<!--recent-->" + '<ul class="news recent">' + "".join(li) + "</ul><!--/recent-->"


_parsed.sort(key=lambda mb: mb[0]["path"] == "")   # トップは最後に作る（ほかのページの更新日を使うため）
for meta, body in _parsed:
    path = meta["path"]
    if path == "":
        body = body.replace("{{recent_updates}}", recent_html())
    _chain = crumbs(path)
    if _chain:
        body = crumb_html(_chain) + body
    root = "/" if path == "404.html" else ("../" * path.count("/") or "./")
    cur = ' aria-current="page"'
    nav = "\n".join(f'    <a href="{root}{p}"{cur if k == meta.get("nav") else ""}>{label}</a>' for k, p, label in NAV)
    scripts = "\n".join(f'<script src="{root}assets/{s}.js"></script>' for s in meta.get("scripts", "").split())
    noindex = meta.get("noindex") == "yes"
    rep = {"title": meta["title"], "description": meta["description"], "canonical": f"{SITE_URL}/{path}",
           "robots": '<meta name="robots" content="noindex">' if noindex else "", "adsense_head": adsense_head(),
           "analytics_note": analytics_note(), "head_extra": ga_head() + '<meta name="google-site-verification" content="ZgxID967oum-2Mm1F5BCX9gvQE_vNl2ZDbXXWfyYP10" />', "nav": nav, "scripts": scripts, "operator": OPERATOR, "operator_intro": OPERATOR_INTRO,
           "contact_block": contact_block(), "policy_date": POLICY_DATE, "ad": ad_block(), "gacha_cards": _gacha_cards,
           "og_image": og_image(meta, path)}
    # トップのランキングカードの評価日は、ランキングページ（src/ranking/ranking.json）の評価日を自動で使う（管理人指示 2026-11-10）。{{rk_date_roman}} など
    for _k, _d in DECKS.items():   # デッキページの title の「○選」（デッキの数。自動）
        rep["deck_count_" + _k] = str(len(_d["list"]))
    for _k, _r in charpages._RANKING.get("ranking", {}).items():
        rep["rk_date_" + _k] = f'【評価日{_r["評価日"]}】' if _r.get("評価日") else ""
    if meta.get("school") in DECKS:
        body = body.replace('<p class="muted">読み込み中…</p>', static_decks(meta["school"]))
        # deck.js がキャラ名をキャラページへのリンクにするための表（キャラ名→ページ）
        body += f'<script>window.CHAR_PAGES={_json.dumps(charpages.CHAR_PATHS, ensure_ascii=False)}</script>\n'
    html = layout.replace("{{content}}", body)
    for _ in range(2):  # 本文の中の {{root}} なども置き換える
        for k, v in rep.items():
            html = html.replace("{{" + k + "}}", v)
        html = html.replace("{{root}}", root)
    for f, v in ver.items():
        html = html.replace(f'assets/{f}"', f'assets/{f}?v={v}"')
    if meta.get("school"):
        html = html.replace('<body data-root=', f'<body data-school="{meta["school"]}" data-root=', 1)
    if _chain:
        html = html.replace("</head>", f'<script type="application/ld+json">{crumb_ld(_chain)}</script>\n</head>', 1)
    if path == "":
        site = {"@context": "https://schema.org", "@type": "WebSite", "name": "パワプロアプリ攻略ベース", "url": SITE_URL + "/"}
        html = html.replace("</head>", f'<script type="application/ld+json">{json.dumps(site, ensure_ascii=False)}</script>\n</head>', 1)
    dest = out / (path if path.endswith(".html") else path + "index.html")
    dest.parent.mkdir(parents=True, exist_ok=True)
    _rel = dest.relative_to(out).as_posix()
    _lm = None
    if not noindex:
        # lastmod：中身が前回と同じなら前回の日付のまま、変わっていたら今日（デッキページは育成日の方が新しければそちら）
        _u = f"{SITE_URL}/{path}"
        _lm = _old_lastmod.get(_u) if _old_html.get(_rel) == _norm(html) else date.today().isoformat()
        if not _lm:   # 中身は同じだが前回の日付が無い → そのページを最後にコミットした日
            _lm = _sp.run(["git", "log", "-1", "--format=%cs", "--", f"docs/{_rel}"], cwd=here, capture_output=True, text=True).stdout.strip() or None
        _dd = deck_dates.get(meta.get("school"))
        if _dd and (not _lm or _dd > _lm):
            _lm = _dd
        urls.append((_u, _lm))
        _pub = first_published(path)   # 「最近の更新」で更新日が同じページは公開日が新しい順
        if _lm:
            _icon = meta.get("og_icon") or (f"img/chars/{path.split('/')[1]}.png" if re.fullmatch(r"chars/\d{4}/", path) else None)
            _page_info.append((path, meta.get("recent_title") or CRUMB.get(path, path), _lm, _pub, next((l for pre, l in OG_LABEL if path.startswith(pre)), ""),
                               _icon if _icon and (out / _icon).exists() else None))
        if path.startswith(DATED) and _lm:
            _pub = min(_pub, _lm)
            html = html.replace("</h1>", f'</h1><p class="pubdate">公開日 <time datetime="{_pub}">{ymd(_pub)}</time>・更新日 <time datetime="{_lm}">{ymd(_lm)}</time></p>', 1)
            art = {"@context": "https://schema.org", "@type": "Article", "headline": meta["title"].split("｜")[0],
                   "datePublished": _pub, "dateModified": _lm, "image": f"{SITE_URL}/img/og/{path.strip('/').replace('/', '_')}.png",
                   "author": {"@type": "Person", "name": OPERATOR, "url": f"{SITE_URL}/about/"}}
            html = html.replace("</head>", f'<script type="application/ld+json">{json.dumps(art, ensure_ascii=False)}</script>\n</head>', 1)
    dest.write_text(html, encoding="utf-8")

# URLを変えたページ：古いURLに「新しいURLへ自動で移動するページ」を置く（検索結果や過去のリンクから来た人のため）。
# サイトのURLは「-」を使わず「_」で統一（2026-11-12 りょーつー指示）。古いURL → 新しいURL
REDIRECTS = [("guide/how-to-read/", "guide/how_to_read/"), ("guide/cost-tool/", "guide/cost_tool/"), ("ranking/next-batter/", "ranking/next_batter/")]
for _old, _new in REDIRECTS:
    _to = f"{SITE_URL}/{_new}"
    _d = out / _old
    _d.mkdir(parents=True, exist_ok=True)
    (_d / "index.html").write_text(
        '<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n<meta name="color-scheme" content="light">\n'
        f'<title>ページが移動しました｜パワプロアプリ攻略ベース</title>\n<link rel="canonical" href="{_to}">\n'
        f'<meta http-equiv="refresh" content="0; url={_to}">\n'
        f'<script>location.replace("/{_new}" + location.search + location.hash)</script>\n</head>\n'
        f'<body style="background:#fff;color:#222">\n<p>このページは移動しました。自動で移動しない場合は <a href="{_to}">こちら</a> を開いてください。</p>\n</body>\n</html>\n', encoding="utf-8")

if (out / "tier").exists():
    urls.append((f"{SITE_URL}/tier/", None))
if (out / "pawaque").exists():
    for page in sorted((out / "pawaque").rglob("index.html")):
        urls.append((f"{SITE_URL}/{page.parent.relative_to(out).as_posix()}/", None))
urls.append((f"{SITE_URL}/roman_costchecker/", None))  # コスト計算ツール（別リポジトリ roman_costchecker。同じドメインの下で公開）
(out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                 + "".join(f"  <url><loc>{u}</loc>" + (f"<lastmod>{m}</lastmod>" if m else "") + "</url>\n" for u, m in urls) + "</urlset>\n", encoding="utf-8")
(out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
if ADSENSE_CLIENT:
    (out / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
if CUSTOM_DOMAIN:
    (out / "CNAME").write_text(CUSTOM_DOMAIN + "\n", encoding="utf-8")
(out / ".nojekyll").write_text("", encoding="utf-8")
print(f"docs/ を作りました（{len(urls)}ページ）")
