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
CONTACT_FORM = "https://forms.gle/QkvV8i98YKqHsFyr6"                             # Googleフォームの URL（https://forms.gle/...）
GA_ID = "G-F98XGNW3LS"                                    # Googleアナリティクス4の測定ID（G-XXXXXXXXXX）。空なら解析なし
POLICY_DATE = "2026年10月"                    # プライバシーポリシーの制定日

NAV = [("home", "", "トップ"), ("roman", "decks/roman/", "ロマン開花學園<small>投手</small>"),
       ("andromeda", "decks/andromeda/", "アンドロメダ学園<small>野手</small>"), ("about", "about/", "このサイトについて")]

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


if out.exists():
    shutil.rmtree(out)
shutil.copytree(src / "assets", out / "assets")
shutil.copytree(src / "img", out / "img")
(out / "data").mkdir()
shutil.copy(chars, out / "data" / "chars.json")
shutil.copy(src / "decks.js", out / "assets" / "decks.js")

layout = (src / "layout.html").read_text(encoding="utf-8")
urls = []
for page in sorted((src / "pages").glob("*.html")):
    text = page.read_text(encoding="utf-8")
    meta_txt, body = re.match(r"<!--(.*?)-->\n(.*)", text, re.S).groups()
    meta = dict(re.findall(r"^(\w+):[ \t]*(.*)$", meta_txt, re.M))
    path = meta["path"]
    root = "/" if path == "404.html" else ("../" * path.count("/") or "./")
    cur = ' aria-current="page"'
    nav = "\n".join(f'    <a href="{root}{p}"{cur if k == meta.get("nav") else ""}>{label}</a>' for k, p, label in NAV)
    scripts = "\n".join(f'<script src="{root}assets/{s}.js"></script>' for s in meta.get("scripts", "").split())
    noindex = meta.get("noindex") == "yes"
    rep = {"title": meta["title"], "description": meta["description"], "canonical": f"{SITE_URL}/{path}",
           "robots": '<meta name="robots" content="noindex">' if noindex else "", "adsense_head": adsense_head(),
           "analytics_note": analytics_note(), "head_extra": ga_head() + '<meta name="google-site-verification" content="ZgxID967oum-2Mm1F5BCX9gvQE_vNl2ZDbXXWfyYP10" />', "nav": nav, "scripts": scripts, "operator": OPERATOR, "operator_intro": OPERATOR_INTRO,
           "contact_block": contact_block(), "policy_date": POLICY_DATE, "ad": ad_block()}
    html = layout.replace("{{content}}", body)
    for _ in range(2):  # 本文の中の {{root}} なども置き換える
        for k, v in rep.items():
            html = html.replace("{{" + k + "}}", v)
        html = html.replace("{{root}}", root)
    if meta.get("school"):
        html = html.replace('<body data-root=', f'<body data-school="{meta["school"]}" data-root=', 1)
    if path == "":
        site = {"@context": "https://schema.org", "@type": "WebSite", "name": "パワプロアプリ攻略ベース", "url": SITE_URL + "/"}
        html = html.replace("</head>", f'<script type="application/ld+json">{json.dumps(site, ensure_ascii=False)}</script>\n</head>', 1)
    dest = out / (path if path.endswith(".html") else path + "index.html")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    if not noindex:
        urls.append(f"{SITE_URL}/{path}")

today = date.today().isoformat()
(out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                 + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
(out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
if ADSENSE_CLIENT:
    (out / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
if CUSTOM_DOMAIN:
    (out / "CNAME").write_text(CUSTOM_DOMAIN + "\n", encoding="utf-8")
(out / ".nojekyll").write_text("", encoding="utf-8")
print(f"docs/ を作りました（{len(urls)}ページ）")
