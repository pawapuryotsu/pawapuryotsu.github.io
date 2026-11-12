# ガチャ記事の「周回ごとの完成確率」を計算して src/gacha/<id>.tables.json に書く。
# ガチャのデータ（src/gacha/<id>.json）を足したら、このスクリプトを1回実行してから build.py を実行する。
#   python3 gacha_calc/build_tables.py
# 計算のしかた：そのステップ数まで引き終わってから、手持ちの目当てキャラを「一番成功率が高い順番」で合成した場合の完成確率（全パターンを調べた正確な値）。
# 合成のルールは guide/limit_break/ のとおり（+5素材の45%・75%は推測値）。同じレアリティで上限開放済みのカードは同時に1枚だけ育てる前提。
import json, subprocess, sys, functools, pathlib
import numpy as np

here = pathlib.Path(__file__).parent
root = here.parent
S, C, D = 24, 34, 60      # 表の大きさ（SR・PR・Rの枚数の上限。これ以上は同じ値として扱う＝少し控えめな値になる）
LOW = [.30, .33, .36, .39, .42]


# ---- SR Lv45（SR+5）：手持ち → 完成確率 ----
@functools.lru_cache(None)
def VSR(n, c0, t, d0, u):
    if n <= 0:
        return 1.0
    b = 0.0
    def lf(lv, rest):
        if lv == 5:
            return .45 * VSR(n - 2, *rest) + .55 * VSR(n - 1, *rest)
        return LOW[lv] * VSR(n - 1, *rest) + (1 - LOW[lv]) * VSR(n, *rest)
    if c0 > 0: b = max(b, lf(0, (c0 - 1, t, d0, u)))
    if t > 0: b = max(b, lf(t, (c0, 0, d0, u)))
    if c0 > 0 and 0 < t < 5: b = max(b, VSR(n, c0 - 1, t + 1, d0, u))
    if c0 > 1 and t == 0: b = max(b, VSR(n, c0 - 2, 1, d0, u))
    def r2(lv, c0n, d0n, un):
        if t > 0: base, cc = t, c0n
        elif c0n > 0: base, cc = 0, c0n - 1
        else: return 0.0
        def res(g):
            return VSR(n, cc, min(5, base + g), d0n, un) if base + g > 0 else VSR(n, cc + 1, 0, d0n, un)
        if lv == 5: return .45 * res(2) + .55 * res(1)
        return LOW[lv] * res(1) + (1 - LOW[lv]) * res(0)
    if t < 5:
        if d0 > 0: b = max(b, r2(0, c0, d0 - 1, u))
        if u > 0: b = max(b, r2(u, c0, d0, 0))
    if d0 > 0 and 0 < u < 5: b = max(b, VSR(n, c0, t, d0 - 1, u + 1))
    if d0 > 1 and u == 0: b = max(b, VSR(n, c0, t, d0 - 2, 1))
    return b


def psr_table():
    """PSR Lv50（PSR+5）：手持ち → 完成確率。C で全パターンを計算（数秒）。[n-1][SR][PR][R]"""
    exe = here / "psr_table"
    binf = root / "src" / "assets" / "gacha_vpsr_f32.tmp"
    subprocess.run(["gcc", "-O2", "-o", str(exe), str(here / "psr_table.c")], check=True)
    subprocess.run([str(exe), str(binf)], stdin=subprocess.DEVNULL, check=True)
    v = np.fromfile(binf, dtype=np.float32).reshape(5, S + 1, C + 1, D + 1).astype(float)
    binf.unlink(); exe.unlink()
    # ブラウザの「引いてみる」用（0〜255に丸めた表）
    (root / "src" / "assets" / "gacha_vpsr.bin").write_bytes(np.clip(np.round(v * 255), 0, 255).astype(np.uint8).tobytes())
    return v


def slot_probs(g, slot):
    """1枠で目当てキャラが各レアリティで出る確率"""
    out = {}
    for r, p in slot["rarity"].items():
        out[r] = p / 100 * (1 if slot["target"] == "only" else g["share"][r] / 100)
    return out


AX = {"PSR": 0, "SR": 1, "PR": 2, "R": 3}


def shift(P, ax):
    R = np.zeros_like(P)
    a = [slice(None)] * 4; b = [slice(None)] * 4; e = [slice(None)] * 4
    a[ax] = slice(1, None); b[ax] = slice(None, -1); e[ax] = -1
    R[tuple(a)] += P[tuple(b)]
    R[tuple(e)] += P[tuple(e)]
    return R


def main():
    vp = psr_table()
    files = sorted(p for p in (root / "src" / "gacha").glob("*.json") if not p.name.endswith(".tables.json"))
    for f in files:
        g = json.loads(f.read_text(encoding="utf-8"))
        P = np.zeros((7, S + 1, C + 1, D + 1)); P[0, 0, 0, 0] = 1
        sr_t, psr_t = [], []
        for st in range(90):
            step = g["steps"][st % len(g["steps"])] if g.get("loop") else g["steps"][min(st, len(g["steps"]) - 1)]
            for slot in step["slots"]:
                pr = slot_probs(g, slot)
                for _ in range(slot["n"]):
                    Q = P * (1 - sum(pr.values()))
                    for k, p in pr.items():
                        Q += p * shift(P, AX[k])
                    P = Q
            # SR Lv45：ベースはSR。2枚目以降のSRとPSRは100%で+1
            tot = 0.0
            for a in range(7):
                for s in range(1, S + 1):
                    m = P[a, s]
                    if m.sum() == 0: continue
                    need = 5 - (s - 1) - a
                    if need <= 0: tot += m.sum(); continue
                    tot += (m * np.array([[VSR(need, min(c, C), 0, min(d, D), 0) for d in range(D + 1)] for c in range(C + 1)])).sum()
            sr_t.append(round(float(tot) * 100, 2))
            tp = P[6].sum()
            for a in range(1, 6):
                tp += (P[a] * vp[5 - (a - 1) - 1]).sum()
            psr_t.append(round(float(tp) * 100, 2))
            if sr_t[-1] >= 99.9 and psr_t[-1] >= 99.5 and (st + 1) % len(g["steps"]) == 0:
                break
        out = {"SR45": sr_t, "PSR50": psr_t}
        (f.parent / (f.stem + ".tables.json")).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f.stem, "SR45:", sr_t[2::3][:6], "PSR50:", psr_t[2::3][:12])


main()
