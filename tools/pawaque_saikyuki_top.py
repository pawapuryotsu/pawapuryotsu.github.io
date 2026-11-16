"""パワクエ西球記のトップ（src/pages/pawaque-saikyuki.html）の「関連ページのリンク欄」と「最新の掲載状況」を、
クエスト一覧・神前試合まとめ・ミッション報酬のデータから作る（2026-11-16 管理人「トップがスカスカ」）。
数字やメモはデータに入っているものだけを使う（推測で書かない）。
使い方： python3 tools/pawaque_saikyuki_top.py → python3 build.py
（tools/pawaque_quest_list.py と tools/pawaque_shinzen_list.py の最後でも自動で呼ばれる）
ページの <!-- SKTOP:START --> と <!-- SKTOP:END --> の間を書き換える。
中身がまだのページは READY を False にすると「準備中」と表示し、リンクにしない（そのページには noindex: yes も書く）。原稿を入れたら True にして noindex を消す。"""
import html, json, re
from pathlib import Path

here = Path(__file__).resolve().parent.parent
e = html.escape
Q = json.loads((here / "src/pawaque_data/saikyuki_quests.json").read_text(encoding="utf-8"))["クエスト"]
S = json.loads((here / "src/pawaque_data/saikyuki_shinzen.json").read_text(encoding="utf-8"))["対戦相手"]
M = json.loads((here / "src/pawaque_data/mission.json").read_text(encoding="utf-8"))
page = here / "src/pages/pawaque-saikyuki.html"

# 中身ができたら True にする
READY = {"drop": False, "contract": False}

# 入力済みのクエスト（むずクエなどはタイトルが無いので、ボスドロップが入っていれば入力済みとみなす）
done = [q for q in Q if q.get("タイトル") or q.get("ボスドロップ")]
nums = [q["番号"] for q in done if re.fullmatch(r"[①-⑳]", q["番号"])]
extra = [q["番号"] for q in done if not re.fullmatch(r"[①-⑳]", q["番号"])]
qrange = f"{nums[0]}〜{nums[-1]}" if len(nums) > 1 else (nums[0] if nums else "")
qrange = "・".join([x for x in [qrange] if x] + extra)
mis = next((len(s["ミッション"]) for s in M if s["ストーリー"] == "西球記"), 0)


def qid(q):
    return "q" + str(Q.index(q) + 1)


def memo(t):
    return e(t.replace("|", ""))


def card(href, img, alt, w, h, label, sub, ready=True):
    sub_html = f'<span class="sk-s">{sub}</span>' if ready else '<span class="sk-s sk-wait">準備中</span>'
    # 準備中のページはリンクにしない（noindex で検索にも出さない。2026-11-17 管理人「準備中のものは公開しない」）
    tag, attr = ("a", f' href="{{{{root}}}}{href}"') if ready else ("div", "")
    return (f'    <{tag} class="sk-c{"" if ready else " sk-off"}"{attr}><span class="sk-th sk-img"><img src="{{{{root}}}}img/pawaque/{img}" '
            f'alt="{e(alt)}" width="{w}" height="{h}"></span><span class="sk-l">{label}</span>{sub_html}</{tag}>')


out = ['  <section class="sk-nav" aria-label="西球記の関連ページ">',
       '  <p class="sk-nav-h">西球記の攻略ページ</p>',
       '  <div class="sk-grid">',
       card("pawaque/saikyuki/feature/", "saikyuki_logo.png", "西球記のロゴ", 235, 130,
            '西球記の<span class="cp-nw">固有ギミック</span>', "仙術・神前試合マス・<wbr>祈願エンディングマス"),
       card("pawaque/saikyuki/quest/", "saikyuki_link_quest.jpg", "クエスト一覧の画面", 374, 148,
            "クエスト一覧", f"{qrange}の<wbr>ドロップ・管理人メモ" if qrange else "準備中"),
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

block = "\n".join(out)
s = page.read_text(encoding="utf-8")
assert "<!-- SKTOP:START -->" in s and "<!-- SKTOP:END -->" in s, "SKTOP の目印が見つからない"
s = re.sub(r"(<!-- SKTOP:START -->).*?(<!-- SKTOP:END -->)", lambda m: m.group(1) + "\n" + block + "\n  " + m.group(2), s, flags=re.S)
page.write_text(s, encoding="utf-8")
print("ok トップ", qrange, len(S), "校", mis, "件")
