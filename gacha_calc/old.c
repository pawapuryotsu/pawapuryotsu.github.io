/* 旧バージョンのカードも使うときの計算の本体。src/assets/gacha_old.js から WebAssembly（src/assets/gacha_old.wasm）として呼ぶ。
   作り直すとき（このファイルを変えたら必ず）：
     clang --target=wasm32 -O3 -nostdlib -Wl,--no-entry -Wl,--export=solve -Wl,--export=alloc -Wl,--export=reset \
           -Wl,--export=pull -Wl,--export=eval_step -o src/assets/gacha_old.wasm gacha_calc/old.c
   状態（旧カードの残り＋作りかけの新カード）と合成の一覧は gacha_old.js が作って渡す。
   セルの並び：[PR][R][PSR][SR]、各セルに n=1..5（あと何段階）。 */
typedef unsigned char u8;
extern u8 __heap_base;
static unsigned long brk_ = 0;
void *alloc(unsigned long n) {
  if (!brk_) brk_ = (unsigned long)&__heap_base;
  unsigned long p = (brk_ + 15) & ~15ul;
  brk_ = p + n;
  unsigned long pages = __builtin_wasm_memory_size(0);
  if (brk_ > pages * 65536) {
    unsigned long need = (brk_ - pages * 65536 + 65535) / 65536;
    if (__builtin_wasm_memory_grow(0, need) == (unsigned long)-1) return 0;
  }
  return (void *)p;
}
void reset(void) { brk_ = (unsigned long)&__heap_base; }

/* NS：状態の数。order：同じセルの中で計算する順番。mStart/mNeed：状態ごとの合成（need＝使う新カード 0=R 1=PR 2=SR 3=PSR、-1＝使わない）。
   oStart/oP/oJ/oD：合成ごとの結果（確率・移る状態×5・ベースが上がる段階）。dims＝{PR,R,PSR,SR の大きさ}。
   term[セル×5+n-1]＝旧カードを使い終わったあとの完成確率。out に最初の状態（状態0）の値を書く。buf＝作業用（(N2*N3*N0+1)*NS*5 個）。 */
void solve(int NS, const int *order, const int *mStart, const signed char *mNeed, const int *oStart,
           const float *oP, const int *oJ, const signed char *oD, const int *dims, const float *term, float *out, float *buf,
           const int *aS, const int *aK, const int *aU, const int *aJ, const float *aux, float *Z) {
  const int N1 = dims[0], N0 = dims[1], N3 = dims[2], N2 = dims[3];
  const int STR[4] = { N2 * N3, N2 * N3 * N0, 1, N2 };
  const int ring = N2 * N3 * N0 + 1, RS = NS * 5;
  int h[4], cell = 0;
  for (h[1] = 0; h[1] < N1; h[1]++) for (h[0] = 0; h[0] < N0; h[0]++) for (h[3] = 0; h[3] < N3; h[3]++) for (h[2] = 0; h[2] < N2; h[2]++, cell++) {
    float *cur = buf + (long)(cell % ring) * RS;
    const float *tv = term + (long)cell * 5;
    int n0 = 0;                       /* tv が 1 の n は、どの状態でも 1（合成を調べなくてよい） */
    while (n0 < 5 && tv[n0] >= 1.0f) n0++;
    /* 「下のランクを全部使って旧カードを上げる」手：使ったあとの手持ち（下のランク0枚）のセルの値 Z を見る */
    const int low0 = h[1] == 0 && h[0] == 0;                 /* PR・R が 0 枚のセル（最初の N3*N2 個） */
    const float *Z5 = Z + (long)(h[3] * N2 + h[2]) * RS;     /* 種類5（SRを上げる）：PR・R が 0 */
    const float *Z4 = Z;                                      /* 種類4（PSRを上げる。PSR目標だけ）：SR・PR・R が 0 */
    const float *ax = aux + (long)cell * 10;
    for (int oi = 0; oi < NS; oi++) {
      const int i = order[oi];
      float best[5];
      for (int n = 0; n < 5; n++) best[n] = tv[n];
      if (n0 < 5) for (int q = aS[i]; q < aS[i + 1]; q++) {
        const float *z; float p;
        if (aK[q] == 5) { if (low0) continue; z = Z5; p = ax[5 + aU[q] - 1]; }
        else { if (low0 && h[2] == 0) continue; z = Z4; p = ax[aU[q] - 1]; }
        if (p <= 0) continue;
        for (int n = n0; n < 5; n++) { float v = p * z[aJ[q] + n] + (1 - p) * z[i * 5 + n]; if (v > best[n]) best[n] = v; }
      }
      if (n0 < 5) for (int m = mStart[i]; m < mStart[i + 1]; m++) {
        const int k = mNeed[m];
        const float *src = cur;
        if (k >= 0) { if (h[k] == 0) continue; src = buf + (long)((cell - STR[k]) % ring) * RS; }
        const int o0 = oStart[m], o1 = oStart[m + 1];
        float v[5] = {0, 0, 0, 0, 0};
        for (int o = o0; o < o1; o++) {
          const float p = oP[o]; const float *w = src + oJ[o]; const int d = oD[o];
          if (d == 0) { v[0] += p * w[0]; v[1] += p * w[1]; v[2] += p * w[2]; v[3] += p * w[3]; v[4] += p * w[4]; }
          else for (int n = 0; n < 5; n++) v[n] += p * (n < d ? 1.0f : w[n - d]);
        }
        for (int n = n0; n < 5; n++) if (v[n] > best[n]) best[n] = v[n];
      }
      float *w = cur + i * 5;
      for (int n = 0; n < 5; n++) w[n] = best[n];
    }
    if (low0) for (int j = 0; j < RS; j++) Z[(long)(h[3] * N2 + h[2]) * RS + j] = cur[j];
    for (int n = 0; n < 5; n++) out[(long)cell * 5 + n] = cur[n];
  }
}

/* ---- ガチャを引いたあとの手持ちの確率（build_tables.py と同じ計算） ---- */
#define TS 24
#define TC 34
#define TD 60
#define NA 7
/* 1枠引く。P[PSR 0..6][SR][PR][R]（上限を超えた分は上限と同じ扱い）。p[0..3]＝目当てキャラが PSR・SR・PR・R で出る確率 */
void pull(double *P, const double *p) {
  const long st[4] = { (long)(TS + 1) * (TC + 1) * (TD + 1), (long)(TC + 1) * (TD + 1), TD + 1, 1 };
  const int mx[4] = { NA - 1, TS, TC, TD };
  const double keep = 1 - p[0] - p[1] - p[2] - p[3];
  int h[4];
  long i = (long)NA * st[0] - 1;
  for (h[0] = mx[0]; h[0] >= 0; h[0]--) for (h[1] = mx[1]; h[1] >= 0; h[1]--) for (h[2] = mx[2]; h[2] >= 0; h[2]--) for (h[3] = mx[3]; h[3] >= 0; h[3]--, i--) {
    double v = P[i] * keep;
    for (int k = 0; k < 4; k++) {
      if (p[k] == 0) continue;
      if (h[k] > 0) v += p[k] * P[i - st[k]];
      if (h[k] == mx[k]) v += p[k] * P[i];
    }
    P[i] = v;
  }
}
/* 今の手持ちの確率 P から、Lv40・SR Lv45・PSR Lv50 の達成確率を out[0..2] に書く。
   Wp＝PSR目標の表 [PR][R][SR][n-1]、Ws＝SR目標の表 [PR][R][PSR 0..4][SR(ベース以外) 0..4][n-1]。kq・ks＝PSR像・SR像の枚数（ベースに使う） */
void eval_step(const double *P, const float *Wp, const float *Ws, int kq, int ks, double *out) {
  double lv = 0, sr = 0, ps = 0;
  long i = 0;
  for (int a = 0; a < NA; a++) for (int s = 0; s <= TS; s++) for (int c = 0; c <= TC; c++) for (int d = 0; d <= TD; d++, i++) {
    const double p = P[i];
    if (p == 0) continue;
    const long cd = (long)c * (TD + 1) + d;
    if (a >= 1) {   /* PSR Lv50：ベースはPSR。2枚目以降のPSRとPSR像は100%で+1 */
      const int n = 5 - (a - 1) - kq;
      ps += n <= 0 ? p : p * Wp[(cd * (TS + 1) + s) * 5 + n - 1];
      lv += p;      /* Lv40：PSRが1枚でもあれば到達 */
    }
    if (s >= 1) {   /* SR：ベースはSR。2枚目以降のSRとPSRは100%で+1（旧カードの素材にもできる） */
      const int x = s - 1, n5 = 5 - ks, n3 = 3 - ks;
      sr += (n5 <= 0 || a + x >= n5) ? p : p * Ws[((cd * 5 + a) * 5 + x) * 5 + n5 - 1];
      if (a == 0) lv += (n3 <= 0 || x >= n3) ? p : p * Ws[((cd * 5 + 0) * 5 + x) * 5 + n3 - 1];
    }
  }
  out[0] = lv; out[1] = sr; out[2] = ps;
}
