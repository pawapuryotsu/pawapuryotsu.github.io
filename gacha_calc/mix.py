# 目当てキャラの別バージョン（通常版など）も同じガチャから出るとき（json の "mix"）の、周回ごとの確率。build_tables.py から呼ばれる。
#   "mix": {"n": 120}＝出現率アップではない n 人の中に別バージョンが1人入っている（出現割合は n 人で均一）。
#   → share の枠で、そのレアリティが出たとき (100 − share)% ÷ n の確率で別バージョン（+0）が出る。
# 計算のしかた：ガチャで出た「今回のバージョンの枚数」と「別バージョンの枚数」の組み合わせごとの確率を出し、
#   別バージョンの手持ちごとに、旧バージョンの入力欄と同じ方法（src/assets/gacha_old.js の手の一覧＋gacha_calc/old.c）で完成確率の表を作って掛け合わせる。
#   ・別バージョンは CAP の枚数まで数える（それより多く出た分は使わない＝少し控えめな値）。
#   ・合成の順番を全部は調べていないので、本当に一番良い手順より少し低く出ることがある（gacha_calc/old_check/README.md）。
#   ・表は丸める前の値（vs・vp）を使うので、別バージョンが1枚も出ない場合は今までの計算と同じ値になる。
# 博士像の全組み合わせ（PSR像・SR像・PR像・R像）を計算するので、1つのガチャで数十分かかる。結果は gacha_calc/cache/ に保存して使い回す。
import ctypes, hashlib, json, pathlib, re, subprocess, tempfile, itertools, os
import numpy as np
from multiprocessing import Pool

here = pathlib.Path(__file__).parent
CAP = (2, 1, 1, 1)          # 別バージョンを何枚まで数えるか（R, PR, SR, PSR）
AXN = {"PSR": 0, "SR": 1, "PR": 2, "R": 3}      # 今回のバージョン：P の軸（別バージョンの4軸のあと）
AXO = {"R": 0, "PR": 1, "SR": 2, "PSR": 3}      # 別バージョン：P の軸
F32 = np.ctypeslib.ndpointer(np.float32, flags="C")
I32 = np.ctypeslib.ndpointer(np.int32, flags="C")
I8 = np.ctypeslib.ndpointer(np.int8, flags="C")


def build_lib():
    """old.c（ブラウザ用）の計算部分を、そのままここで使える形にする"""
    src = (here / "old.c").read_text(encoding="utf-8")
    src = re.sub(r"extern u8 __heap_base;.*?\nvoid reset\(void\)[^\n]*\n", "", src, flags=re.S)
    assert "__builtin_wasm" not in src
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "old_native.c").write_text(src, encoding="utf-8")
    subprocess.run(["gcc", "-O3", "-shared", "-fPIC", "-o", str(d / "old.so"), str(d / "old_native.c")], check=True)
    return str(d / "old.so")


def shift(P, ax):
    """軸 ax の枚数を1増やす（上限では上限のまま）"""
    R = np.zeros_like(P)
    a = [slice(None)] * P.ndim; b = [slice(None)] * P.ndim; e = [slice(None)] * P.ndim
    a[ax] = slice(1, None); b[ax] = slice(None, -1); e[ax] = -1
    R[tuple(a)] += P[tuple(b)]
    R[tuple(e)] += P[tuple(e)]
    return R


def slot_probs(g, slot):
    """1枠で [今回のバージョンが各レアリティで出る確率, 別バージョンが各レアリティで出る確率]"""
    new, old = {}, {}
    for r, p in slot["rarity"].items():
        t = slot["target"]
        new[r] = p / 100 * (1 if t in ("pick", "only") else g["share"][r] / 100)
        if t == "share":
            old[r] = p / 100 * (100 - g["share"][r]) / 100 / g["mix"]["n"]
    return new, old


def distribution(g, T, S, C, D):
    """ステップごとの手持ちの確率 [ステップ][別R][別PR][別SR][別PSR][PSR 0..6][SR][PR][R]（float32）"""
    P = np.zeros(tuple(c + 1 for c in CAP) + (7, S + 1, C + 1, D + 1))
    start = [0, 0, 0, 0]
    for x in g.get("extra", []):
        start[AXN[x["rarity"]]] += x["n"]
    P[0, 0, 0, 0, min(start[0], 6), min(start[1], S), min(start[2], C), min(start[3], D)] = 1
    out = []
    L = len(g["steps"])
    for st in range(T):
        step = g["steps"][st % L] if g.get("loop") else g["steps"][min(st, L - 1)]
        for slot in step["slots"]:
            new, old = slot_probs(g, slot)
            for _ in range(slot["n"]):
                Q = P * (1 - sum(new.values()) - sum(old.values()))
                for k, p in new.items():
                    Q += p * shift(P, 4 + AXN[k])
                for k, p in old.items():
                    Q += p * shift(P, AXO[k])
                P = Q
        out.append(P.astype(np.float32))
    return out


_W = {}


def _init(lib_path, vs, vp, Pt, dims):
    lib = ctypes.CDLL(lib_path)
    lib.solve.argtypes = [ctypes.c_int, I32, I32, I8, I32, F32, I32, I8, I32, F32, F32, F32, I32, I32, I32, I32, F32, F32]
    lib.solve.restype = None
    _W.update(lib=lib, vs=vs, vp=vp, Pt=Pt, dims=dims)


def _solve(gr, dims, term, aux):
    if gr["empty"]:      # 別バージョンが0枚のときは、今までの表そのまま（今までの計算と同じ値になる）
        return np.ascontiguousarray(term, np.float32).reshape(-1)
    lib = _W["lib"]
    NS = gr["NS"]
    cells = dims[0] * dims[1] * dims[2] * dims[3]
    out = np.zeros(cells * 5, np.float32)
    buf = np.zeros((dims[3] * dims[2] * dims[1] + 1) * NS * 5, np.float32)
    Z = np.zeros(dims[2] * dims[3] * NS * 5, np.float32)
    i32 = lambda k, pad=0: np.ascontiguousarray(np.array(gr[k] + [0] * pad, np.int32))
    lib.solve(NS, i32("order"), i32("mStart"), np.ascontiguousarray(np.array(gr["mNeed"] + [0], np.int8)), i32("oStart"),
              np.ascontiguousarray(np.array(gr["oP"] + [0], np.float32)), i32("oJ", 1), np.ascontiguousarray(np.array(gr["oD"] + [0], np.int8)),
              np.array(dims, np.int32), np.ascontiguousarray(term, np.float32), out, buf,
              i32("aS"), i32("aK", 1), i32("aU", 1), i32("aJ", 1), np.ascontiguousarray(aux, np.float32), Z)
    return out


def _pool_job(args):
    """別バージョンの手持ち1通りについて、[SR45, LV40, PSR50] への寄与（今回のバージョンの手持ちの確率を掛けたもの）を返す"""
    row, = args
    S, C, D, KS, KL = _W["dims"]
    vs, vp = _W["vs"], _W["vp"]
    o = tuple(row["pool"])
    Pt = _W["Pt"][(slice(None),) + o]                  # [ステップ][PSR][SR][PR][R]
    T = Pt.shape[0]
    mass = Pt.reshape(T, 7, S + 1, -1).sum(axis=3, dtype=np.float64)   # [ステップ][PSR][SR]
    sr45 = np.zeros((T, KS + 1, KL + 1, KL + 1)); lv40 = np.zeros_like(sr45)
    psr50 = np.zeros((T, KS + 1, KS + 1, KL + 1, KL + 1))
    if mass.sum() == 0:
        return sr45, lv40, psr50
    # ---- SR目標（SR Lv45・Lv40）：手持ち＝[PR][R][PSR 0..4][ベース以外のSR 0..4] ----
    ax = np.arange(5)
    need = np.arange(1, 6)[None, None, :] - ax[:, None, None] - ax[None, :, None]      # [PSR][SR][n-1] → あと何段階
    Psr = np.ascontiguousarray(Pt[:, :5, 1:6].astype(np.float64))                     # [ステップ][PSR 0..4][x=SR-1 0..4][PR][R]
    aux = np.zeros((C + 1, D + 1, 5, 5, 10), np.float32)
    aux[..., 5:] = np.moveaxis(vs[0, 0], 0, -1)[:, :, None, None, :]
    for kp in range(KL + 1):
        for kr in range(KL + 1):
            v = np.moveaxis(vs[kp, kr], 0, -1)                                         # [PR][R][n-1]
            term = np.where(need[None, None] <= 0, 1.0, v[:, :, np.clip(need - 1, 0, 4)])   # [PR][R][PSR][SR][n-1]
            Ws = _solve(row["2"], [C + 1, D + 1, 5, 5], term, aux).reshape(C + 1, D + 1, 5, 5, 5).astype(np.float64)
            dots = np.einsum("taxcd,cdaxn->taxn", Psr, Ws)                              # [ステップ][PSR][x][n-1]
            for ks in range(KS + 1):
                n5, n3 = 5 - ks, 3 - ks
                for a in range(7):
                    for s in range(1, S + 1):
                        x = s - 1
                        sr45[:, ks, kp, kr] += mass[:, a, s] if (n5 <= 0 or a + x >= n5) else dots[:, a, x, n5 - 1]
                        if a == 0:
                            lv40[:, ks, kp, kr] += mass[:, 0, s] if (n3 <= 0 or x >= n3) else dots[:, 0, x, n3 - 1]
                lv40[:, ks, kp, kr] += mass[:, 1:].sum(axis=(1, 2))
    # ---- PSR目標：手持ち＝[PR][R][SR]（2枚目以降のPSRとPSR像は全部ベースに使う） ----
    Pp = np.ascontiguousarray(Pt[:, 1:6].reshape(T * 5, -1))                           # [ステップ×PSR 1..5][SR,PR,R]
    aux = np.zeros((C + 1, D + 1, S + 1, 10), np.float32)
    aux[..., :5] = np.transpose(vp[0, 0, 0], (2, 3, 1, 0))                             # [n-1][SR][PR][R] → [PR][R][SR][n-1]
    aux[..., 5:] = np.moveaxis(vs[0, 0], 0, -1)[:, :, None, :]
    for ks in range(KS + 1):
        for kp in range(KL + 1):
            for kr in range(KL + 1):
                term = np.transpose(vp[ks, kp, kr], (2, 3, 1, 0))
                Wp = _solve(row["3"], [C + 1, D + 1, 1, S + 1], term, aux).reshape(C + 1, D + 1, S + 1, 5)
                dots = (Pp @ np.ascontiguousarray(np.transpose(Wp, (2, 0, 1, 3)).reshape(-1, 5))).reshape(T, 5, 5).astype(np.float64)   # [ステップ][PSR-1][n-1]
                for kq in range(KS + 1):
                    t = mass[:, 6].sum(axis=1).copy()
                    for a in range(1, 6):
                        n = 5 - (a - 1) - kq
                        t += mass[:, a].sum(axis=1) if n <= 0 else dots[:, a - 1, n - 1]
                    psr50[:, kq, ks, kp, kr] += t
    return sr45, lv40, psr50


def mix_tables(g, T, vs, vp, S, C, D, KS, KL):
    """戻り値：sr45[ステップ][SR像][PR像][R像], lv40[同じ], psr50[ステップ][PSR像][SR像][PR像][R像]（別バージョン込みの確率）"""
    key = hashlib.md5(json.dumps([g["steps"], g["share"], g["mix"]["n"], g.get("extra", []), bool(g.get("loop")), T, CAP, S, C, D, KS, KL,
                                  (here / "old.c").read_text(encoding="utf-8"), (here / "mix_graph.js").read_text(encoding="utf-8"),
                                  (here.parent / "src" / "assets" / "gacha_old.js").read_text(encoding="utf-8"),
                                  hashlib.md5(vs.tobytes()).hexdigest()], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
    name = f"mix_{g['id']}_{key}.npz"
    for d in (here / "cache", pathlib.Path("/mnt/project-files/gacha-calc")):
        if (d / name).exists():
            z = np.load(d / name)
            return z["sr45"], z["lv40"], z["psr50"]
    print(f"{g['id']}：別バージョン込みの確率を計算します（数十分）…", flush=True)
    pools = [list(p) for p in itertools.product(*[range(c + 1) for c in CAP])]
    tmp = pathlib.Path(tempfile.mkdtemp()) / "graph.json"
    subprocess.run(["node", str(here / "mix_graph.js"), json.dumps(pools), str(tmp)], check=True)
    rows = json.loads(tmp.read_text())
    Pt = np.stack(distribution(g, T, S, C, D))        # [ステップ][別R][別PR][別SR][別PSR][PSR][SR][PR][R]
    for r in rows:
        r["2"]["empty"] = r["3"]["empty"] = not any(r["pool"])
    rows.sort(key=lambda r: -r["3"]["NS"])            # 重いものから
    with Pool(os.cpu_count(), initializer=_init, initargs=(build_lib(), vs, vp, Pt, (S, C, D, KS, KL))) as pool:
        res = pool.map(_pool_job, [(r,) for r in rows], chunksize=1)
    sr45, lv40, psr50 = (sum(r[i] for r in res) for i in range(3))
    (here / "cache").mkdir(exist_ok=True)
    np.savez_compressed(here / "cache" / name, sr45=sr45, lv40=lv40, psr50=psr50)
    return sr45, lv40, psr50
