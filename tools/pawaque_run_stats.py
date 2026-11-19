"""西球記のクエスト周回ページ（例：⑱道中2 /pawaque/saikyuki/q18/）の「入手出来るアイテム」を、
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
n = len(runs)
RAR = ["金", "銀", "銅"]
ITEM = re.compile(r"(秘伝書|攻略本|巻物|お札|ノ書|呼び寄せの香|金丹|リュック|カバン|指輪|ドリンク)")


def is_item(name):
    return bool(ITEM.search(name))


areas = sorted({x["area"] for r in runs for x in r["drops"] if x.get("area")})
y, m, d = D["取得日"].split("-")
out = [f'  <p class="rs-note">管理人の周回記録 <b>{n}周分</b>（{int(m)}/{int(d)}時点）から集計しています。<span class="cp-nw">周回が増えたら更新します。</span>管理人が記録対象にしていないアイテムは表に入っていません。</p>']

for a in areas:
    cnt = defaultdict(Counter)   # 名前 → レア度ごとの個数
    runs_with = defaultdict(set)
    con = Counter()
    for r in runs:
        for x in r["drops"]:
            if x.get("area") != a:
                continue
            if is_item(x["name"]):
                cnt[x["name"]][x["rarity"]] += 1
                runs_with[x["name"]].add(r["no"])
            else:
                con[x["rarity"]] += 1
    rows = sorted(cnt, key=lambda k: (-sum(cnt[k].values()), k))
    out += [f'  <h3 class="rs-h">エリア{a}</h3>', '  <div class="bt-wrap"><table class="bt rs-t">',
            '  <thead><tr><th>アイテム</th><th>出た周</th><th>金</th><th>銀</th><th>銅</th></tr></thead><tbody>']
    for k in rows:
        c = cnt[k]
        out.append(f'  <tr><th>{e(k)}</th><td>{len(runs_with[k])}/{n}周</td>' + "".join(f'<td>{c[r] or "-"}</td>' for r in RAR) + '</tr>')
    if con:
        out.append(f'  <tr class="rs-con"><th>契約書（合計）</th><td>{sum(con.values())}枚</td>' + "".join(f'<td>{con[r] or "-"}</td>' for r in RAR) + '</tr>')
    out.append('  </tbody></table></div>')

# ボスドロップ（記録で選ばれている周だけ）
bk = [r for r in runs if r.get("boss")]
if bk:
    out += [f'  <h3 class="rs-h">ボスドロップ</h3>', f'  <p class="rs-note">ボスドロップを記録した{len(bk)}周分です。</p>',
            '  <div class="bt-wrap"><table class="bt rs-t">', '  <thead><tr><th>エリア</th><th>ドロップ</th><th>レア度</th></tr></thead><tbody>']
    for a in areas:
        c = Counter()
        for r in bk:
            s = r["boss"].get(str(a))
            if s is None:
                continue
            if s == -1:
                c[("なし", "")] += 1
                continue
            x = next((x for x in r["drops"] if x.get("slot") == s), None)
            if x:
                c[(x["name"] if is_item(x["name"]) else "契約書", x["rarity"])] += 1
            else:   # カウンターで「記録する」を外した物（何かは記録に無い）
                c[("記録対象外のアイテム", "")] += 1
        first = True
        for (nm, rr), v in sorted(c.items(), key=lambda t: (t[0][0] == "なし", t[0][0] == "記録対象外のアイテム", t[0][0] == "契約書", t[0][0], RAR.index(t[0][1]) if t[0][1] in RAR else 9)):
            out.append(f'  <tr>' + (f'<th rowspan="{len(c)}">エリア{a}</th>' if first else '') + f'<td class="rs-l">{e(nm)}{"" if v == 1 else f"（{v}回）"}</td><td>{e(rr) or "-"}</td></tr>')
            first = False
    out.append('  </tbody></table></div>')

# 祈願
pr = [(r, p) for r in runs for p in (r.get("prayers") or [])]
if pr:
    ok = sum(p["result"] == "成功" for _, p in pr)
    out += [f'  <h3 class="rs-h">祈願の記録</h3>', f'  <p class="rs-note">{len(pr)}回中、成功{ok}回・失敗{len(pr) - ok}回。</p>',
            '  <div class="bt-wrap"><table class="bt rs-t">', '  <thead><tr><th>アイテム</th><th>結果</th><th>付いたスキル</th></tr></thead><tbody>']
    for r, p in pr:
        res = '<span class="tx-b tx-bold">成功</span>' if p["result"] == "成功" else '<span class="tx-r tx-bold">失敗</span>'
        out.append(f'  <tr><th>{e(p["name"])}</th><td>{res}</td><td class="rs-l">{e("・".join(p.get("gained") or [])) or "-"}</td></tr>')
    out.append('  </tbody></table></div>')

block = "\n".join(out)
s = page.read_text(encoding="utf-8")
assert "<!-- RUNS:START -->" in s and "<!-- RUNS:END -->" in s, "RUNS の目印が見つからない"
s = re.sub(r"(<!-- RUNS:START -->).*?(<!-- RUNS:END -->)", lambda m_: m_.group(1) + "\n" + block + "\n  " + m_.group(2), s, flags=re.S)
page.write_text(s, encoding="utf-8")
print("ok", pid, n, "周")
