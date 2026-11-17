"""パワクエ西球記のトップ（src/pages/pawaque-saikyuki.html）の「関連ページのリンク欄」と「最新の掲載状況」を、
クエスト一覧・神前試合まとめ・ミッション報酬のデータから作る（2026-11-16 管理人「トップがスカスカ」）。
数字やメモはデータに入っているものだけを使う（推測で書かない）。
使い方： python3 tools/pawaque_saikyuki_top.py → python3 build.py
（tools/pawaque_quest_list.py と tools/pawaque_shinzen_list.py の最後でも自動で呼ばれる）
ページの <!-- SKTOP:START --> と <!-- SKTOP:END --> の間を書き換える。
中身がまだのページは READY を False にするとカードごと出さない（そのページには noindex: yes も書く）。原稿を入れたら True にして noindex を消す。"""
import html, json, re
from pathlib import Path

here = Path(__file__).resolve().parent.parent
e = html.escape
Q = json.loads((here / "src/pawaque_data/saikyuki_quests.json").read_text(encoding="utf-8"))["クエスト"]
S = json.loads((here / "src/pawaque_data/saikyuki_shinzen.json").read_text(encoding="utf-8"))["対戦相手"]
M = json.loads((here / "src/pawaque_data/mission.json").read_text(encoding="utf-8"))
page = here / "src/pages/pawaque-saikyuki.html"

# 中身ができたら True にする
READY = {"drop": True, "contract": False}

# 入力済みのクエスト（むずクエなどはタイトルが無いので、ボスドロップが入っていれば入力済みとみなす）
done = [q for q in Q if q.get("タイトル") or q.get("ボスドロップ")]
nums = [q["番号"] for q in done if re.fullmatch(r"[①-⑳]", q["番号"])]
extra = [q["番号"] for q in done if not re.fullmatch(r"[①-⑳]", q["番号"])]
qrange = f"{nums[0]}〜{nums[-1]}" if len(nums) > 1 else (nums[0] if nums else "")
qparts = [x for x in [qrange] if x] + extra
qrange = "・".join(qparts)
# カードの小さい字では「むずク|エ」のように途中で折り返さないよう、項目ごとにまとめる
qrange_nw = "・".join(f'<span class="cp-nw">{x}</span>' for x in qparts)
mis = next((len(s["ミッション"]) for s in M if s["ストーリー"] == "西球記"), 0)


def qid(q):
    return "q" + str(Q.index(q) + 1)


def memo(t):
    # 管理人メモの {青:…}＝青文字・{青太:…}＝青太字・{赤:…}＝赤文字（2026-11-17 管理人）
    s = e(t.replace("|", ""))
    for tag, cls in (("青太", "em-blue"), ("青", "tx-b"), ("赤太", "em-red"), ("赤", "tx-r")):
        s = re.sub(r"\{" + tag + r":(.*?)\}", lambda m: f'<span class="{cls}">{m.group(1)}</span>', s)
    return s


def card(href, img, alt, w, h, label, sub, ready=True):
    # 準備中のページはカードごと出さない（2026-11-17 管理人「カードごと消す」）。原稿が入ったら READY を True に
    if not ready:
        return None
    return (f'    <a class="sk-c" href="{{{{root}}}}{href}"><span class="sk-th sk-img"><img src="{{{{root}}}}img/pawaque/{img}" '
            f'alt="{e(alt)}" width="{w}" height="{h}"></span><span class="sk-l">{label}</span><span class="sk-s">{sub}</span></a>')


out = ['  <section class="sk-nav" aria-label="西球記の関連ページ">',
       '  <p class="sk-nav-h">西球記の攻略ページ</p>',
       '  <div class="sk-grid">',
       card("pawaque/saikyuki/feature/", "saikyuki_logo.png", "西球記のロゴ", 235, 130,
            '西球記の<span class="cp-nw">固有ギミック</span>', "仙術・神前試合マス・<wbr>祈願エンディングマス"),
       card("pawaque/saikyuki/quest/", "saikyuki_link_quest.jpg", "クエスト一覧の画面", 374, 148,
            "クエスト一覧", f"{qrange_nw}の<wbr>ドロップ・管理人メモ" if qrange else "準備中"),
       card("pawaque/saikyuki/muzu/", "saikyuki_link_muzu.jpg", "むずクエ エリア3のマップ", 360, 150,
            'むずクエ<span class="cp-nw">攻略＆周回</span>', 'エリアごとの<wbr><span class="cp-nw">ルートと仙術</span>'),
       card("pawaque/saikyuki/drop/", "saikyuki_link_drop.jpg", "交渉の指輪", 311, 121,
            '重要アイテム<span class="cp-nw">周回方法</span>', "", READY["drop"]),
       card("pawaque/saikyuki/shinzen/", "saikyuki_link_shinzen.jpg", "神前試合の画面", 660, 334,
            '神前試合<span class="cp-nw">まとめ</span>', f"{len(S)}校の進化対象・<wbr>スカウト候補"),
       card("pawaque/saikyuki/contract/", "saikyuki_link_contract.jpg", "［求道者］才賀 侑人の契約書", 320, 125,
            'ドロップ<span class="cp-nw">契約書まとめ</span>', "", READY["contract"]),
       card("pawaque/mission/", "saikyuki_link_mission.jpg", "ミッションの画面", 232, 161,
            "ミッション報酬", f"西球記の{mis}件を<wbr>掲載" if mis else ""),
       '  </div>', '  </section>', '',
       '  <h2 id="about">西球記とは</h2>',
       '  <p><span class="cp-nw">「西球記（さいきゅうき）」</span>は、パワクエの5つ目のストーリーです。<span class="em-blue">2026/11/16 14時に配信されました。</span></p>', '']

# 最新の掲載状況
out += ['  <h2 id="now">最新の掲載状況</h2>', '  <ul>']
if qrange:
    out.append(f'    <li><a href="{{{{root}}}}pawaque/saikyuki/quest/">クエスト一覧</a>：{qrange}を<span class="cp-nw">載せています。</span></li>')
out.append(f'    <li><a href="{{{{root}}}}pawaque/saikyuki/shinzen/">神前試合まとめ</a>：{len(S)}校を<span class="cp-nw">載せています。</span></li>')
if mis:
    out.append(f'    <li><a href="{{{{root}}}}pawaque/mission/">ミッション報酬まとめ</a>：西球記の{mis}件を<span class="cp-nw">載せています。</span></li>')
out += ['  </ul>', '  <p>遊んで分かったことから順に<span class="cp-nw">追記します。</span></p>', '']

# 期間限定の神前試合
lim = [(i, t) for i, t in enumerate(S) if t.get("期間")]
if lim:
    # 神前試合まとめでは期間限定の学校が先頭（t1〜）に並ぶ
    out += ['  <h2 id="limited">期間限定の神前試合</h2>', '  <ul>']
    for n, (_, t) in enumerate(lim, 1):
        out.append(f'    <li><a href="{{{{root}}}}pawaque/saikyuki/shinzen/#t{n}">{e(t["対戦相手"])}</a>'
                   f'<span class="em-red">（※{e(t["期間"])}）</span></li>')
    out += ['  </ul>', '']

# クエストのメモ（青メモ・赤メモ・管理人メモ）
memos = []
for q in done:
    for k, cls in (("青メモ", "em-blue"), ("赤メモ", "em-red"), ("管理人メモ", "")):
        # 改行で区切ったメモは1行ずつ別の項目にする
        for line in (q.get(k) or "").split("\n"):
            if not line:
                continue
            t = memo(line)
            memos.append(f'    <li><a href="{{{{root}}}}pawaque/saikyuki/quest/#{qid(q)}">{e(q["番号"] + q["タイトル"].replace("|", ""))}</a>：'
                         + (f'<span class="{cls}">{t}</span>' if cls else t) + '</li>')
if memos:
    out += ['  <h2 id="memo">クエストのポイント</h2>', '  <ul>'] + memos + ['  </ul>', '']

# 契約書がボスドロップするクエスト
rows = []
for q in done:
    cs = [x for x in q.get("ボスドロップ", "").split("\n") if "契約書" in x]
    if cs:
        items = "、".join(f'<span class="em-blue">{e(x)}</span>' if x.startswith("［") else e(x) for x in cs)
        rows.append(f'    <li><a href="{{{{root}}}}pawaque/saikyuki/quest/#{qid(q)}">{e(q["番号"] + q["タイトル"].replace("|", ""))}</a>：{items}</li>')
if rows:
    out += ['  <h2 id="boss-contract">契約書がボスドロップするクエスト</h2>', '  <ul class="sk-list">'] + rows + ['  </ul>', '']

out = [x for x in out if x is not None]   # 準備中で出さないカードを除く
_n = sum(1 for x in out if x.startswith('    <a class="sk-c"'))
if _n % 3 and _n % 2 == 0:   # PC（3列）で空きマスが出る枚数（4枚など）は、PCを2列ではなく枚数に合わせた列にする
    out = [x.replace('<div class="sk-grid">', f'<div class="sk-grid sk-g{_n if _n <= 4 else 2}">') for x in out]
block = "\n".join(out)
s = page.read_text(encoding="utf-8")
assert "<!-- SKTOP:START -->" in s and "<!-- SKTOP:END -->" in s, "SKTOP の目印が見つからない"
s = re.sub(r"(<!-- SKTOP:START -->).*?(<!-- SKTOP:END -->)", lambda m: m.group(1) + "\n" + block + "\n  " + m.group(2), s, flags=re.S)
page.write_text(s, encoding="utf-8")
print("ok トップ", qrange, len(S), "校", mis, "件")
