# ガチャ記事の「周回ごとの確率」を計算して、次のファイルを書く。
#   src/gacha/<id>.tables.json        … 博士像なしの表（ページに埋め込む）
#   src/assets/gacha_t/<id>.bin       … 博士像ありの表（像の枚数の全組み合わせ。ページが必要なときに読む）
#   src/assets/gacha_v/sr.bin, pX_Y_Z.bin … 「引いてみる」用の、手持ち→完成確率の表（ガチャによらず共通。X,Y,Z＝SR像・PR像・R像の枚数）
# ガチャのデータ（src/gacha/<id>.json）を足したら、このスクリプトを1回実行してから build.py を実行する。
#   python3 gacha_calc/build_tables.py
# 計算のしかた：そのステップ数まで引き終わってから、手持ちの目当てキャラ（と博士像）を「一番成功率が高い順番」で
# 合成した場合の確率（全パターンを調べた正確な値）。合成のルールは guide/limit_break/ のとおり（+5素材の45%は推測値）。
# 同じレアリティで上限開放済みのカードは同時に1枚だけ育てる前提。博士像は同じレアリティのカードを100%で+1。
#
# PSR目標の「手持ち→完成確率」の表は計算に約30分かかる（メモリが足りなければディスクを使う。空き10GB必要）ので、
# 一度計算したら gacha_calc/cache/ に保存して使い回す（ガチャによらず共通。git には入れない）。
# 予備が /mnt/project-files/gacha-calc/ にあればそれを使う。どちらにも無ければ自動で計算し直す。
import json, subprocess, pathlib, shutil
import numpy as np

here = pathlib.Path(__file__).parent
root = here.parent
S, C, D = 24, 34, 60      # 表の大きさ（SR・PR・Rの枚数の上限。これ以上は同じ値として扱う＝少し控えめな値になる）。vtable.c と同じ値にする
KS = 5                    # PSR像・SR像を何枚まで選べるか
KL = 10                   # PR像・R像を何枚まで選べるか
CACHE = f"vpsr_S{S}C{C}D{D}_K{KS}_{KL}_u16.npz"
CACHE_DIRS = [here / "cache", pathlib.Path("/mnt/project-files/gacha-calc")]


def build_exe():
    exe = here / "vtable"
    subprocess.run(["gcc", "-O2", "-o", str(exe), str(here / "vtable.c")], check=True)
    return exe


def sr_table(exe):
    """SR目標：[PR像][R像][あと何段階-1][PR][R] → 完成確率"""
    tmp = here / "sr.tmp"
    subprocess.run([str(exe), "sr", str(tmp), str(KL), str(KL)], stdin=subprocess.DEVNULL, check=True)
    v = np.fromfile(tmp).reshape(KL + 1, KL + 1, 5, C + 1, D + 1)
    tmp.unlink()
    return v


def to_u16(v):
    """0〜65535に丸める。0と65535は「ちょうど0%・100%」のときだけ使う"""
    r = np.clip(np.round(v.astype(np.float64) * 65535), 1, 65534)
    r[v <= 0] = 0
    r[v >= 1] = 65535
    return r.astype(np.uint16)


def psr_table(exe):
    """PSR目標：[SR像][PR像][R像][あと何段階-1][SR][PR][R] → 完成確率"""
    shape = (KS + 1, KL + 1, KL + 1, 5, S + 1, C + 1, D + 1)
    for d in CACHE_DIRS:
        if (d / CACHE).exists():
            return (np.load(d / CACHE)["v"].astype(np.float32) / 65535).reshape(shape)
    print("PSR目標の表を計算します（約1時間半）…")
    tmp = here / "psr.tmp"
    subprocess.run([str(exe), "psr", str(tmp), str(KS), str(KL), str(KL)], check=True)
    u = to_u16(np.fromfile(tmp, dtype=np.float32))
    tmp.unlink()
    (here / "cache").mkdir(exist_ok=True)
    np.savez_compressed(here / "cache" / CACHE, v=u)
    return (u.astype(np.float32) / 65535).reshape(shape)   # キャッシュから読んだときと同じ値にする


def u8(v):
    """0〜255に丸める。0と255は「ちょうど0%・100%」のときだけ使う"""
    r = np.clip(np.round(v * 255), 1, 254)
    r[v <= 0] = 0
    r[v >= 1 - 1e-12] = 255
    return r.astype(np.uint8)


def write_browser_tables(vs, vp):
    out = root / "src" / "assets" / "gacha_v"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "sr.bin").write_bytes(u8(vs).tobytes())
    for ks in range(KS + 1):
        for kp in range(KL + 1):
            for kr in range(KL + 1):
                (out / f"p{ks}_{kp}_{kr}.bin").write_bytes(u8(vp[ks, kp, kr]).tobytes())


def slot_probs(g, slot):
    """1枠で目当てキャラが各レアリティで出る確率。
    target：only＝出現率アップキャラのみの枠、share＝そのレアリティが出たとき share の割合で出現率アップキャラ、
    pick＝選択ガチャ券など、目当てキャラを必ず選べる枠。
    出現率アップキャラが複数（json の "charas"）のときは、only・share の確率を人数で等分する（公式「各イベキャラの出現割合は均一」）"""
    nch = len(g.get("charas") or [None])
    out = {}
    for r, p in slot["rarity"].items():
        t = slot["target"]
        out[r] = p / 100 * (1 if t == "pick" else (1 if t == "only" else g["share"][r] / 100) / nch)
    return out


def variants(f, g):
    """計算する目当てキャラごとに（表のファイル名, そのキャラのデータ）。1キャラのガチャはそのまま1つ"""
    if not g.get("charas"):
        return [(f.stem, g)]
    return [(f"{f.stem}_{c['key']}", dict(g, extra=c.get("extra", []))) for c in g["charas"]]


AX = {"PSR": 0, "SR": 1, "PR": 2, "R": 3}


def shift(P, ax):
    R = np.zeros_like(P)
    a = [slice(None)] * 4; b = [slice(None)] * 4; e = [slice(None)] * 4
    a[ax] = slice(1, None); b[ax] = slice(None, -1); e[ax] = -1
    R[tuple(a)] += P[tuple(b)]
    R[tuple(e)] += P[tuple(e)]
    return R


def sr_goal(vs, W, N, fail=False):
    """W[e]＝「確定の+1がe回分ある」手持ちの確率（[PR][R]）。あとN段階のSR目標の達成確率を [SR像][PR像][R像] で返す
    fail=True（vs は「100%でない」印の表）のときは「失敗するかもしれない手持ち」の確率を返す（0なら本当に100%）"""
    out = np.zeros((KS + 1, KL + 1, KL + 1))
    for e, w in enumerate(W):
        tot = w.sum()
        if tot == 0:
            continue
        for ks in range(KS + 1):
            need = N - e - ks
            if need > 0:
                out[ks] += np.tensordot(vs[:, :, need - 1], w, axes=([2, 3], [0, 1]))
            elif not fail:
                out[ks] += tot
    return out


def main():
    exe = build_exe()
    vs = sr_table(exe)
    vp = psr_table(exe)
    exe.unlink()
    write_browser_tables(vs, vp)
    vpf = vp.reshape((KS + 1) * (KL + 1) ** 2 * 5, -1)
    # 「100%でない」印の表（キャッシュは 65535＝ちょうど100% のときだけなので、1.0 と比べてよい）
    vsx = (vs < 1).astype(np.float64)
    vpx = (vpf < 1).astype(np.float32)
    tdir = root / "src" / "assets" / "gacha_t"
    tdir.mkdir(exist_ok=True)
    files = sorted(p for p in (root / "src" / "gacha").glob("*.json") if not p.name.endswith(".tables.json"))
    for f, g in (v for f in files for v in variants(f, json.loads(f.read_text(encoding="utf-8")))):
        P = np.zeros((7, S + 1, C + 1, D + 1))
        start = [0, 0, 0, 0]   # ガチャ以外で手に入る分（イベント報酬など。json の "extra"）から始める
        for x in g.get("extra", []):
            start[AX[x["rarity"]]] += x["n"]
        P[min(start[0], 6), min(start[1], S), min(start[2], C), min(start[3], D)] = 1
        got_sr, got_psr, sr45, lv40, psr50 = [], [], [], [], []
        fails = {k: [] for k in ('gotSR', 'gotPSR', 'LV40', 'SR45', 'PSR50')}   # 失敗する可能性のある手持ちの確率（0なら本当に100%）
        L = len(g["steps"])
        for st in range(max(90, 40 * L)):   # 最大40周（または90ステップ）。十分な確率になったら周の終わりで止める
            step = g["steps"][st % len(g["steps"])] if g.get("loop") else g["steps"][min(st, len(g["steps"]) - 1)]
            for slot in step["slots"]:
                pr = slot_probs(g, slot)
                for _ in range(slot["n"]):
                    Q = P * (1 - sum(pr.values()))
                    for k, p in pr.items():
                        Q += p * shift(P, AX[k])
                    P = Q
            got_sr.append(P[:, 1:].sum())
            fails['gotSR'].append(P[:, 0].sum())
            fails['gotPSR'].append(P[0].sum())
            got_psr.append(P[1:].sum())
            # SR Lv45：ベースはSR。2枚目以降のSRとPSRは100%で+1 → e = PSRの枚数 + SRの枚数 - 1
            W = [sum(P[a, e + 1 - a] for a in range(7) if 1 <= e + 1 - a <= S) for e in range(5)]
            rest = sum(P[a, s].sum() for a in range(7) for s in range(1, S + 1) if a + s - 1 >= 5)
            sr45.append(sr_goal(vs, W, 5) + rest)
            fails['SR45'].append(sr_goal(vsx, W, 5, True) + P[:, 0].sum())
            # Lv40：PSRが1枚でもあれば到達。無ければSRを+3に
            lv40.append(sr_goal(vs, [P[0, e + 1] for e in range(3)], 3) + P[0, 4:].sum() + P[1:].sum())
            fails['LV40'].append(sr_goal(vsx, [P[0, e + 1] for e in range(3)], 3, True) + P[0, 0].sum())
            # PSR Lv50：ベースはPSR。2枚目以降のPSRとPSR像は100%で+1
            dots = (vpf @ P[1:6].reshape(5, -1).astype(np.float32).T).reshape(KS + 1, KL + 1, KL + 1, 5, 5)   # [SR像][PR像][R像][n-1][PSRの枚数-1]
            dotx = (vpx @ P[1:6].reshape(5, -1).astype(np.float32).T).reshape(KS + 1, KL + 1, KL + 1, 5, 5)
            t = np.zeros((KS + 1, KS + 1, KL + 1, KL + 1))
            tx = np.full((KS + 1, KS + 1, KL + 1, KL + 1), P[0].sum())
            for kq in range(KS + 1):
                t[kq] += P[6].sum()
                for a in range(1, 6):
                    need = 5 - (a - 1) - kq
                    t[kq] += P[a].sum() if need <= 0 else dots[:, :, :, need - 1, a - 1]
                    if need > 0:
                        tx[kq] += dotx[:, :, :, need - 1, a - 1]
            psr50.append(t)
            fails['PSR50'].append(tx)
            if sr45[-1][0, 0, 0] >= .999 and psr50[-1][0, 0, 0, 0] >= .995 and (st + 1) % L == 0:
                break
        # %で小数4桁まで。100 は「ちょうど100%」のときだけ（それ以外は 99.9999 まで）
        # 計算の誤差で1に見えても、失敗する可能性のある手持ちが残っていれば100%にしない
        pct = lambda xs, k: [100.0 if np.ravel(m)[0] == 0 else min(round(float(x) * 100, 4), 99.9999) for x, m in zip(xs, fails[k])]   # [0]＝博士像なし
        out = {"KS": KS, "KL": KL, "gotSR": pct(got_sr, "gotSR"), "gotPSR": pct(got_psr, "gotPSR"), "LV40": pct([x[0, 0, 0] for x in lv40], "LV40"),
               "SR45": pct([x[0, 0, 0] for x in sr45], "SR45"), "PSR50": pct([x[0, 0, 0, 0] for x in psr50], "PSR50")}
        (root / "src" / "gacha" / (f + ".tables.json")).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        # 博士像ありの表：[SR45][LV40][PSR50] の順、各 [像の組み合わせ][ステップ]、値は 確率×65535（uint16。0と65535はちょうど0%・100%のときだけ）
        def u16(x, k):
            v = np.moveaxis(np.array(x, dtype=float), 0, -1)
            r = np.clip(np.round(v * 65535), 1, 65534)
            r[v <= 0] = 0
            r[np.moveaxis(np.array(fails[k], dtype=float), 0, -1) == 0] = 65535
            return r.astype("<u2").tobytes()
        (tdir / (f + ".bin")).write_bytes(u16(sr45, "SR45") + u16(lv40, "LV40") + u16(psr50, "PSR50"))
        print(f, "ステップ数", len(sr45))
        for k in ("gotSR", "gotPSR", "LV40", "SR45", "PSR50"):
            print("  ", k, [round(v, 2) for v in out[k][L - 1::L][:12]])


main()
