"""西球記のクエスト周回ページ（例：⑱道中2 /pawaque/saikyuki/q18/）の「周回記録」を、
管理人の「パワクエ周回カウンター」の記録から作る（2026-11-19 管理人「周回データをここに反映」）。
記録の写し：src/pawaque_data/saikyuki_runs_<id>.json（管理人に「反映して」と言われた時に、カウンターの runs から
そのクエストの周だけを書き出して上書きする。fp などの読み取り用データは入れない）。
使い方： python3 tools/pawaque_run_stats.py q18 → python3 build.py
ページの <!-- RUNS:START --> と <!-- RUNS:END --> の間を書き換える。数字は記録そのまま（推測で足さない）。"""
import html, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

here = Path(__file__).resolve().parent.parent
e = html.escape
pid = sys.argv[1] if len(sys.argv) > 1 else "q18"
D = json.loads((here / f"src/pawaque_data/saikyuki_runs_{pid}.json").read_text(encoding="utf-8"))
page = here / f"src/pages/pawaque-saikyuki-{pid}.html"
runs = D["runs"]
# 記録対象外（管理人が誤ってチェックしていた物など）は集計から外す
SKIP = set(D.get("記録対象外") or [])
for r in runs:
    r["drops"] = [x for x in r["drops"] if x["name"] not in SKIP]
n = len(runs)
RAR = ["金", "銀", "銅"]
ITEM = re.compile(r"(秘伝書|攻略本|巻物|お札|ノ書|呼び寄せの香|金丹|リュック|カバン|指輪|ドリンク)")


def is_item(name):
    return bool(ITEM.search(name))


y, m, d = D["取得日"].split("-")

# 並び順（2026-11-19 管理人）：西球記専用 → マス強化 → その他 → 契約書
def group(name):
    if re.search(r"(ノ書|呼び寄せの香|金丹)", name):
        return 0
    if re.search(r"(攻略本|秘伝書)", name):
        return 1
    return 2


def vname(name):
    # 契約書の名前：[バージョン] は全角の［］に
    return name.replace("[", "［").replace("]", "］") + "の契約書"


def table(cnt, con, extra=(), cls="", named=None):
    """金・銀・銅・合計の表。cnt＝{アイテム名: Counter(レア度)}、con＝契約書の Counter(レア度)、extra＝[(名前, 回数)]（合計だけの行）"""
    rows = sorted(cnt, key=lambda k: (group(k), -sum(cnt[k].values()), k))
    t = [f'  <div class="bt-wrap"><table class="bt rs-t{cls}">',
         '  <thead><tr><th>アイテム</th><th>金</th><th>銀</th><th>銅</th><th>合計</th></tr></thead><tbody>']
    for k in rows:
        c = cnt[k]
        t.append(f'  <tr><th>{e(k)}</th>' + "".join(f'<td>{c[r] or "-"}</td>' for r in RAR) + f'<td class="rs-sum">{sum(c.values())}</td></tr>')
    if con:
        t.append('  <tr class="rs-con"><th>契約書</th>' + "".join(f'<td>{con[r] or "-"}</td>' for r in RAR) + f'<td class="rs-sum">{sum(con.values())}</td></tr>')
    # ボスの契約書はキャラ名ごと（2026-11-19 管理人）
    # ［バージョン］付きを上に（2026-11-19 管理人）
    for k in sorted(named or {}, key=lambda k: (not k.startswith("["), -sum(named[k].values()), k)):
        c = named[k]
        t.append(f'  <tr class="rs-con"><th>{e(vname(k))}</th>' + "".join(f'<td>{c[r] or "-"}</td>' for r in RAR) + f'<td class="rs-sum">{sum(c.values())}</td></tr>')
    for nm, v in extra:
        t.append(f'  <tr class="rs-con"><th>{e(nm)}</th><td>-</td><td>-</td><td>-</td><td class="rs-sum">{v}</td></tr>')
    t.append('  </tbody></table></div>')
    return t


COACH = ("コーチ人数+3", "コーチ人数+4")


def render(runs, note, hp=""):
    """周の一覧から「周回記録」の中身（エリアごとの表・コーチ・祈願）を作る。note(周数)＝先頭の説明文、hp＝祈願の見出しの頭"""
    areas = sorted({x["area"] for r in runs for x in r["drops"] if x.get("area")})
    # 道中とボスを分けて集計（2026-11-19 管理人）。どれがボスか分かる周（ボスを記録した周）だけを使う
    bk = [r for r in runs if r.get("boss")]
    nb = len(bk)
    out = [note(nb)]
    for a in areas:
        road, boss = defaultdict(Counter), defaultdict(Counter)
        rcon, bcon = Counter(), defaultdict(Counter)
        none = other = 0
        for r in bk:
            sl = r["boss"].get(str(a))
            for x in r["drops"]:
                if x.get("area") != a:
                    continue
                isb = sl is not None and sl >= 0 and x.get("slot") == sl
                if is_item(x["name"]):
                    (boss if isb else road)[x["name"]][x["rarity"]] += 1
                else:
                    if isb:
                        bcon[x["name"]][x["rarity"]] += 1
                    else:
                        rcon[x["rarity"]] += 1
            if sl == -1:
                none += 1
            elif sl is not None and not any(x.get("slot") == sl for x in r["drops"]):
                other += 1   # カウンターで「記録する」を外した物（何かは記録に無い）
        extra = [(nm, v) for nm, v in (("記録対象外のアイテム", other), ("ボスドロップなし（祈願）" if a == areas[-1] else "ボスドロップなし", none)) if v]
        out += [f'  <div class="rs-area">', f'  <h3 class="rs-area-h">エリア{a}</h3>', f'  <p class="rs-sub">エリア{a}道中</p>'] + table(road, rcon)
        out += [f'  <p class="rs-sub">エリア{a}ボス</p>'] + table(boss, None, extra, " rs-boss", bcon)
        # コーチ人数+3・+4が付いた契約書（全周から。祈願で付いた・増えたものは（祈願））
        coach = []
        for r in runs:
            gained = {(p["name"], g) for p in (r.get("prayers") or []) if p.get("result") == "成功" for g in (p.get("gained") or [])}
            for x in r["drops"]:
                if x.get("area") == a and not is_item(x["name"]):
                    cs = [k + ("（祈願）" if (x["name"], k) in gained else "") for k in (x.get("skills") or []) if k in COACH]
                    if cs:
                        coach.append((x, cs))
        if coach:
            out.append('  <div class="rs-coach-box"><p class="rs-coach-h">コーチ人数+3・+4が付いた契約書</p>')
            out.append('  <ul class="rs-coach">' + "".join(
                f'<li>{e(vname(x["name"]))}（{e(x["rarity"])}）：<span class="em-blue cp-nw">{e("・".join(cs))}</span></li>' for x, cs in coach) + '</ul></div>')
        out.append('  </div>')

    # 祈願
    pr = [(r, p) for r in runs for p in (r.get("prayers") or [])]
    if pr:
        ok = sum(p["result"] == "成功" for _, p in pr)
        out += ['  <div class="rs-area rs-pray">', f'  <h3 class="rs-area-h">{hp}祈願の記録</h3>', f'  <p class="rs-note">{len(pr)}回中、成功{ok}回・失敗{len(pr) - ok}回。</p>',
                '  <div class="bt-wrap"><table class="bt rs-t">', '  <thead><tr><th>アイテム</th><th>結果</th><th>付いたスキル</th></tr></thead><tbody>']
        for r, p in pr:
            res = '<span class="tx-b tx-bold">成功</span>' if p["result"] == "成功" else '<span class="tx-r tx-bold">失敗</span>'
            out.append(f'  <tr><th>{e(p["name"].replace("[", "［").replace("]", "］"))}</th><td>{res}</td><td class="rs-l">{e("・".join(p.get("gained") or [])) or "-"}</td></tr>')
        out.append('  </tbody></table></div>\n  </div>')
    return out


# 期間ごとに分ける（2026-11-19 管理人）：カウンターの「期間」が新しい周を表に出し、
# 終わった期間（例：らんま1/2コラボ期間、11/26 でコラボキャラの契約書が出なくなる）は
# 「○○の記録はこちらをタップ」のボタンを押すと開く形でしまう。期間が1つだけの時はボタン無し。
NAMES = D.get("期間の表示名", {})
periods = []
for r in runs:
    k = r.get("period") or ""
    if k not in periods:
        periods.append(k)
by = {k: [r for r in runs if (r.get("period") or "") == k] for k in periods}
# 説明文（2026-11-19 管理人の文面）
MEMO = "<br>総合練習の攻略本・秘伝書や○○の巻物など、有用性がないアイテムを記録対象外のアイテムとしています。<br>道中の契約書は、神前試合マスで獲得したものも含みます。"


def note_now(nb):
    return f'  <p class="rs-note">周回記録 <b>{nb}周分</b>（{int(m)}/{int(d)}時点）から集計しています。{MEMO}</p>'


out = render(by[periods[-1]], note_now)
for k in reversed(periods[:-1]):
    nm = NAMES.get(k, k or "以前")
    rs = by[k]
    old = render(rs, lambda nb: f'  <p class="rs-note">{e(nm)}の周回記録 <b>{nb}周分</b>から集計しています。{MEMO}</p>', e(nm) + "の")
    out += [f'  <details class="rs-old"><summary>{e(nm)}の記録は<span class="cp-nw">こちらをタップ</span></summary><div class="rs-old-in">'] + old + ['  </div></details>']

block = "\n".join(out)
s = page.read_text(encoding="utf-8")
assert "<!-- RUNS:START -->" in s and "<!-- RUNS:END -->" in s, "RUNS の目印が見つからない"
s = re.sub(r"(<!-- RUNS:START -->).*?(<!-- RUNS:END -->)", lambda m_: m_.group(1) + "\n" + block + "\n  " + m_.group(2), s, flags=re.S)
page.write_text(s, encoding="utf-8")
print("ok", pid, n, "周")
