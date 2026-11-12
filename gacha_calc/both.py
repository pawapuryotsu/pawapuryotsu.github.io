# 出現率アップキャラが2人のガチャで「2人とも」目標に届く確率（博士像なし）。build_tables.py から呼ばれる。
# 2人分の手持ちの組み合わせは多すぎて全パターンの正確な計算ができないので、ガチャを N 回試しに引いた結果の割合で出す
# （乱数の種を固定しているので、何度実行しても同じ値）。1回ごとに：
#   - 引き終わってから、選択ガチャ券（target "pick"）を2人にどう分けるかを全通り試し、「2人とも完成する確率」が一番高い分け方を選ぶ
#     （券は取っておける前提。管理人 2026-11-12）
#   - 2人それぞれの手持ちは、1人のときと同じ表（一番成功率が高い合成順）で完成確率を出し、2人の確率を掛ける（合成の成否は2人で別々）
import numpy as np

RS = ["PSR", "SR", "PR", "R"]


def _funcs(vs, vp, S, C, D):
    """手持ち (PSR, SR, PR, R) の配列 → 完成確率。vs＝[あと何段階-1][PR][R]、vp＝[あと何段階-1][SR][PR][R]（どちらも博士像なし）"""
    def look_sr(n, pr, r):
        return vs[np.clip(n, 1, 5) - 1, np.minimum(pr, C), np.minimum(r, D)]

    def lv40(psr, sr, pr, r):
        n = 3 - (sr - 1)
        return np.where(psr > 0, 1.0, np.where(sr == 0, 0.0, np.where(n <= 0, 1.0, look_sr(n, pr, r))))

    def sr45(psr, sr, pr, r):   # 出たPSRもSRの素材にする（1人のときと同じ）
        n = 5 - (psr + sr - 1)
        return np.where(sr == 0, 0.0, np.where(n <= 0, 1.0, look_sr(n, pr, r)))

    def psr50(psr, sr, pr, r):
        n = 5 - (psr - 1)
        v = vp[np.clip(n, 1, 5) - 1, np.minimum(sr, S), np.minimum(pr, C), np.minimum(r, D)]
        return np.where(psr == 0, 0.0, np.where(n <= 0, 1.0, v))

    return {"gotSR": lambda psr, sr, pr, r: (sr > 0).astype(float), "gotPSR": lambda psr, sr, pr, r: (psr > 0).astype(float),
            "LV40": lv40, "SR45": sr45, "PSR50": psr50}


def both_tables(g, vs, vp, S, C, D, N=200000, seed=20261112):
    rng = np.random.default_rng(seed)
    F = _funcs(vs.astype(np.float64), vp, S, C, D)
    cnt = np.zeros((2, 4, N), dtype=np.int64)   # [キャラ][レアリティ][試行]
    for ci, ch in enumerate(g["charas"]):
        for x in ch.get("extra", []):
            cnt[ci, RS.index(x["rarity"])] += x["n"]
    tick = {"SR": 0, "PSR": 0}
    sure = {"SR": [], "PSR": []}   # その時点までにもらえる選択券の枚数
    out = {k: [] for k in F}
    L = len(g["steps"])
    for st in range(40 * L):
        step = g["steps"][st % L] if g.get("loop") else g["steps"][min(st, L - 1)]
        for sl in step["slots"]:
            if sl["target"] == "pick":
                for r, p in sl["rarity"].items():
                    assert p == 100 and r in tick
                    tick[r] += sl["n"]
                continue
            ps = []
            for r in RS:
                p = sl["rarity"].get(r, 0) / 100 * (1 if sl["target"] == "only" else g["share"][r] / 100) / 2
                ps += [p, p]
            ps.append(max(0.0, 1 - sum(ps)))
            m = rng.multinomial(sl["n"], ps, size=N)
            for ri in range(4):
                cnt[0, ri] += m[:, 2 * ri]
                cnt[1, ri] += m[:, 2 * ri + 1]
        nS, nP = tick["SR"], tick["PSR"]
        sure["SR"].append(nS); sure["PSR"].append(nP)
        for k, f in F.items():
            best = np.zeros(N)
            for a in range(nS + 1):        # 乱馬（1人目）に使うSR券の枚数
                for b in range(nP + 1):    # 乱馬に使うPSR券の枚数
                    v = f(cnt[0, 0] + b, cnt[0, 1] + a, cnt[0, 2], cnt[0, 3]) * f(cnt[1, 0] + nP - b, cnt[1, 1] + nS - a, cnt[1, 2], cnt[1, 3])
                    np.maximum(best, v, out=best)
            out[k].append(best.mean())
        if out["PSR50"][-1] >= .995 and (st + 1) % L == 0:
            break
    # %で小数2桁まで。試しに引いた結果なので「ちょうど100%」とは言えない → 最大 99.99（ページでは「ほぼ100%」）
    # ただし「SR・PSRが1枚以上」は、選択券とイベント報酬だけで2人とも必ず持てるときは本当に100%（その時点の券の枚数で判定）
    res = {"KS": 0, "KL": 0, "mc": N, **{k: [min(round(float(x) * 100, 2), 99.99) for x in v] for k, v in out.items()}}
    for k, r in (("gotSR", "SR"), ("gotPSR", "PSR")):
        for i, n in enumerate(sure[r]):
            if n >= sum(1 for ch in g["charas"] if not any(x["rarity"] == r for x in ch.get("extra", []))):
                res[k][i] = 100.0
    return res
