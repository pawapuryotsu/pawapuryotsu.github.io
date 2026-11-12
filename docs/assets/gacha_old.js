// 旧バージョンのカードも使うときの確率を、ブラウザでその場で計算する（Web Worker。gacha.js から呼ぶ）。
// 方式：旧バージョンのカードを先に使い、残った新カードは今までの表（assets/gacha_v。全パターンを調べた最適な合成順）で合成する。
//   旧カードの使い方は、次の手を全部調べて一番成功率が高いものを選ぶ：
//   ・旧カードをベース（完成させる新カード）に合成　・旧カード同士を合成　・+0の新カードを旧カードに合成
//   ・新カード1枚を「作りかけ」にして、旧カード・+0の新カードを合成してからベースや旧カードに合成
//   ・下のランクの新カードを全部使って旧PSR・旧SRを上げる（成功率は今までの表。使ったあと下のランクの新カードは残らない扱い）
//   育てる旧カードは同時に1枚だけ。博士像は旧カードには使わない（ベース用の像は使う。それ以外は残りの新カードの合成で使う）。
// これは「全部の順番を調べた値」ではないので、本当に一番良い手順の確率より少し低く出ることがある
// （検算：gacha_calc/old_check/。周回ごとの表で最大1ポイントほど）。合成ルールは guide/limit_break/ と同じ。
// 計算の本体は gacha_calc/old.c（assets/gacha_old.wasm）。
(function (root) {
  const LOW = [.30, .33, .36, .39, .42], PP = [.05, .07, .09, .11, .13, .15], DIFF = [.5, .55, .6, .65, 1];
  // m を t に合成したときの [確率, 上がる段階] の一覧。合成できない（何も起こらない・未検証）ときは null
  // r：0=R 1=PR 2=SR 3=PSR、v：0=新バージョン 1〜=旧バージョン、l：上限開放の段階
  function merge(m, t, sameUp) {
    if (m.r === t.r) {
      if (m.v === t.v) return m.l === 0 || (m.v > 0 && sameUp) ? [[1, 1]] : null;
      return m.l < 5 ? [[DIFF[m.l], 1]] : [[.75, 3], [.25, 2]];
    }
    if (m.r === t.r - 1) return m.l < 5 ? [[LOW[m.l], 1]] : [[.45, 2], [.55, 1]];
    if (t.r === 3 && m.r === 1) return [[PP[m.l], 1]];
    if (t.r === 3 && m.r === 0) return [[.005, 1]];
    if (m.r === t.r + 1 && m.l === 0) return [[1, 1]];   // 1ランク上の素材は +0 のときだけ（上限開放済みは未検証）
    return null;
  }
  const enc = (c) => ((c.r * 8 + c.v) * 6 + c.l) * 2 + c.o;
  const dec = (k) => ({ o: k & 1, l: (k >> 1) % 6, v: Math.floor((k >> 1) / 6) % 8, r: Math.floor((k >> 1) / 48) });

  // 状態（旧カードの残り＋作りかけの新カード）と、そこからできる合成の一覧を作る
  // goal：3＝PSR目標、2＝SR目標。手持ちの新カード h＝[R, PR, SR, PSR]（ベースは別。PSR目標の PSR は全部ベースに合成する前提）
  function graph(goal, old, opt) {
    const tempR = goal - 1, cons = [true, true, true, goal === 2];
    // 作りかけの新カード（PSR目標なら新SR、SR目標なら新PR）は、そこに合成すると意味がある旧カードがあるときだけ使う
    const tempFrom = goal === 3 ? [1] : [0, 1];
    const useTemp = opt.temp && (goal === 2 || opt.tempPSR) && (opt.tempAlways || old.some((c) => tempFrom.includes(c.r)));
    const key = (P, t) => P.join(",") + "|" + t;
    const states = [], idx = new Map();
    let nMoves = 0;
    const get = (P, t) => {
      P = P.slice().sort((a, b) => a - b);
      const k = key(P, t);
      let i = idx.get(k);
      if (i === undefined) { i = states.length; idx.set(k, i); states.push({ P, t }); }
      return i;
    };
    get(old.map((c) => enc({ r: c.r, v: c.v, l: c.l, o: 0 })), -1);
    for (let si = 0; si < states.length; si++) {
      const { P, t } = states[si];
      const mv = [];
      const mats = [];
      P.forEach((k, i) => { if (i === 0 || P[i - 1] !== k) mats.push({ kind: "o", i, c: dec(k) }); });
      if (opt.newMat !== false || t >= 0) for (let r = 0; r < 4; r++) if (cons[r]) mats.push({ kind: "n", r, c: { r, v: 0, l: 0 } });
      if (t >= 0) mats.push({ kind: "t", c: { r: tempR, v: 0, l: t } });
      for (const m of mats) {
        const rest = m.kind === "o" ? P.filter((_, j) => j !== m.i) : P;
        const t2 = m.kind === "t" ? -1 : t;
        const tg = [];
        const only = t >= 0 && opt.tempOnly;   // 作りかけの新カードがある間は、それを育ててベースに合成する手だけ
        if (m.kind !== "n" && (!only || m.kind === "t")) tg.push({ kind: "b", c: { r: goal, v: 0, l: 0 } });
        if (t >= 0 && m.kind !== "t" && (m.kind === "n" || tempFrom.includes(m.c.r))) tg.push({ kind: "t", c: { r: tempR, v: 0, l: t } });
        const anyOpen = rest.some((k) => k & 1);
        rest.forEach((k, j) => {
          if (only || (j > 0 && rest[j - 1] === k)) return;
          const c = dec(k);
          if (opt.oneOpen && anyOpen && !c.o) return;   // 育てる旧カードは同時に1枚だけ
          if (m.kind === "n" && opt.newMat === false) return;   // 軽い調べ方：+0の新カードは「作りかけ」にだけ合成する
          if (m.kind === "o" && opt.oldOld === false) return;   // 軽い調べ方：旧カード同士は合成しない
          if (c.r === 0 && opt.rTarget === false) return;       // 軽い調べ方：旧Rは育てない
          if (goal === 2 && c.r === 3) return;            // SR目標では、旧PSRを上限開放しても使い道がない（上限開放済みPSRはSRの素材にしない）
          tg.push({ kind: "o", j, c });
        });
        for (const g of tg) {
          const res = merge(m.c, g.c, opt.sameUp);
          if (!res) continue;
          const outs = [];
          let ps = 0;
          for (const [p, dl] of res) {
            ps += p;
            if (g.kind === "b") outs.push([p, get(rest, t2), dl]);
            else if (g.kind === "t") outs.push([p, get(rest, Math.min(5, t + dl)), 0]);
            else { const r2 = rest.slice(); r2[g.j] = enc({ r: g.c.r, v: g.c.v, l: Math.min(5, g.c.l + dl), o: 1 }); outs.push([p, get(r2, t2), 0]); }
          }
          if (ps < 1 - 1e-12) outs.push([1 - ps, get(rest, t2), 0]);
          mv.push({ need: m.kind === "n" ? m.r : -1, outs });
        }
      }
      // 「下のランクの新カードを全部使って、この旧カードを k 段階上げる」手（成功率は今までの表。使ったあと下のランクの新カードは残らない扱い）
      const allin = [];
      if (t < 0 && opt.allIn) {
        const anyOpen = P.some((k) => k & 1);
        P.forEach((k, j) => {
          if (j > 0 && P[j - 1] === k) return;
          const c = dec(k);
          if (opt.oneOpen && anyOpen && !c.o) return;
          const kind = c.r === 3 && goal === 3 ? 4 : c.r === 2 ? 5 : 0;
          if (!kind) return;
          for (let up = 1; c.l + up <= 5; up++) { const r2 = P.slice(); r2[j] = enc({ r: c.r, v: c.v, l: c.l + up, o: 1 }); allin.push([kind, up, get(r2, t)]); }
        });
      }
      states[si].allin = allin;
      if (t < 0 && useTemp && !(opt.tempOnly && P.some((k) => k & 1))) mv.push({ need: tempR, outs: [[1, get(P, 0), 0]] });
      states[si].moves = mv;
      nMoves += mv.length;
      if (opt.maxMoves && nMoves > opt.maxMoves) return null;   // 重すぎる（呼ぶ側で、もっと軽い調べ方に切り替える）
    }
    states.nMoves = nMoves;
    return states;
  }

  // 計算本体（WebAssembly）。term＝Float32Array [PR][R][PSR][SR][n-1]：旧カードを使い終わったあとの完成確率（今までの表）。
  // 戻り値：同じ並びの Float32Array（旧カードを全部持った最初の状態の値）
  // aux＝Float32Array [セル][k-1]×2：下のランクの新カードだけで k 段階上げられる確率（博士像なしの表）。[0]＝PSRを（SR・PR・Rで）、[1]＝SRを（PR・Rで）
  function solve(wasm, st, term, dims, aux) {
    const NS = st.length;
    const size = st.map((s) => s.P.length + (s.t >= 0 ? 1 : 0));
    const order = [...Array(NS).keys()].sort((a, b) => size[a] - size[b]);   // 同じセルの中では、カードの枚数が少ない状態から計算する
    let nm = 0, no = 0, na = 0;
    for (const s of st) { nm += s.moves.length; na += s.allin.length; for (const m of s.moves) no += m.outs.length; }
    const ex = wasm.exports;
    ex.reset();
    const cells = dims[0] * dims[1] * dims[2] * dims[3];
    const ringLen = (dims[3] * dims[2] * dims[1] + 1) * NS * 5;
    const al = (n) => { const p = ex.alloc(n); if (!p) throw new Error("memory"); return p; };
    const pOrder = al(NS * 4), pMS = al((NS + 1) * 4), pNeed = al(nm), pOS = al((nm + 1) * 4), pP = al(no * 4), pJ = al(no * 4), pD = al(no), pDims = al(16),
      pTerm = al(cells * 20), pOut = al(cells * 20), pBuf = al(ringLen * 4),
      pAS = al((NS + 1) * 4), pAK = al(na * 4 + 4), pAU = al(na * 4 + 4), pAJ = al(na * 4 + 4), pAux = al(aux ? cells * 40 : 4), pZ = al(dims[2] * dims[3] * NS * 20);
    const mem = ex.memory.buffer;
    const mStart = new Int32Array(mem, pMS, NS + 1), mNeed = new Int8Array(mem, pNeed, nm), oStart = new Int32Array(mem, pOS, nm + 1),
      oP = new Float32Array(mem, pP, no), oJ = new Int32Array(mem, pJ, no), oD = new Int8Array(mem, pD, no);
    new Int32Array(mem, pOrder, NS).set(order);
    new Int32Array(mem, pDims, 4).set(dims);
    new Float32Array(mem, pTerm, cells * 5).set(term);
    const aS = new Int32Array(mem, pAS, NS + 1), aK = new Int32Array(mem, pAK, na), aU = new Int32Array(mem, pAU, na), aJ = new Int32Array(mem, pAJ, na);
    if (aux) new Float32Array(mem, pAux, cells * 10).set(aux);
    let a = 0, b = 0, q = 0;
    for (let i = 0; i < NS; i++) {
      aS[i] = q;
      for (const [kind, up, j] of st[i].allin) { aK[q] = kind; aU[q] = up; aJ[q] = j * 5; q++; }
      mStart[i] = a;
      for (const m of st[i].moves) { mNeed[a] = m.need; oStart[a] = b; for (const [p, j, d] of m.outs) { oP[b] = p; oJ[b] = j * 5; oD[b] = d; b++; } a++; }
    }
    mStart[NS] = a; oStart[nm] = b; aS[NS] = q;
    ex.solve(NS, pOrder, pMS, pNeed, pOS, pP, pJ, pD, pDims, pTerm, pOut, pBuf, pAS, pAK, pAU, pAJ, pAux, pZ);
    return { out: new Float32Array(ex.memory.buffer, pOut, cells * 5).slice(), states: NS, moves: nm };
  }

  // ---- ここから：ガチャの表と合わせて「周回ごとの確率」を作る ----
  const S = 24, C = 34, D = 60;   // 表の大きさ（gacha_calc/build_tables.py・gacha.js と同じ値）
  // 旧カードの調べ方。上から順に試して、重すぎなければそれを使う（下ほど調べる手が少ない＝軽いが、少し低めに出やすい）
  const TIERS = {
    3: [{ temp: true, tempPSR: true, tempAlways: true }, { temp: true, tempPSR: true }, { temp: true, tempPSR: true, tempOnly: true }, { temp: false },
      { temp: false, rTarget: false }, { temp: false, newMat: false }, { temp: false, newMat: false, oldOld: false }],
    2: [{ temp: true }, { temp: true, tempOnly: true }, { temp: true, tempOnly: true, rTarget: false }, { temp: false, rTarget: false },
      { temp: false, newMat: false }, { temp: false, newMat: false, oldOld: false }],
  };
  const BUDGET = { 3: 4500, 2: 10000 };   // 合成の手の数の上限（PSR目標は1手あたりの計算が重い）
  function plan(goal, old) {
    for (let i = 0; i < TIERS[goal].length; i++) {
      const st = graph(goal, old, Object.assign({ sameUp: true, oneOpen: true, allIn: true, maxMoves: BUDGET[goal] }, TIERS[goal][i]));
      if (st) { st.tier = i; return st; }
    }
    return null;
  }
  // job：{ steps, loop, share, nch, extra, old:[{r,l,n}], dj:{PSR,SR,PR,R}, KL }。get(path)＝assets/ 以下のファイルを ArrayBuffer で返す
  async function run(job, get, progress) {
    const old = [];
    for (const c of job.old) for (let i = 0; i < c.n; i++) old.push({ r: c.r, v: 1, l: c.l });
    const stS = plan(2, old), stP = plan(3, old);
    if (!stS || !stP) return { error: "too_many" };
    progress && progress(1);
    const KL1 = job.KL + 1, dj = job.dj;
    const [wasmBuf, srBuf, p0Buf, pkBuf] = await Promise.all([get("gacha_old.wasm"), get("gacha_v/sr.bin"), get("gacha_v/p0_0_0.bin"),
      get("gacha_v/p" + dj.SR + "_" + dj.PR + "_" + dj.R + ".bin")]);
    const wasm = (await WebAssembly.instantiate(wasmBuf, {})).instance;
    const VS = new Uint8Array(srBuf), VP0 = new Uint8Array(p0Buf), VPk = new Uint8Array(pkBuf);
    const vs = (kp, kr, n, c, d) => VS[(((kp * KL1 + kr) * 5 + n - 1) * (C + 1) + c) * (D + 1) + d] / 255;
    const vp = (T, n, s, c, d) => T[(((n - 1) * (S + 1) + s) * (C + 1) + c) * (D + 1) + d] / 255;
    // SR目標（Lv40・SR Lv45 用）。手持ち＝[PR][R][PSR 0..4][ベース以外のSR 0..4]
    let dims = [C + 1, D + 1, 5, 5], cells = dims[0] * dims[1] * 25;
    let term = new Float32Array(cells * 5), aux = new Float32Array(cells * 10), k = 0, q = 0;
    for (let c = 0; c <= C; c++) for (let d = 0; d <= D; d++) for (let a = 0; a < 5; a++) for (let x = 0; x < 5; x++) {
      for (let n = 1; n <= 5; n++) term[k++] = n - a - x <= 0 ? 1 : vs(dj.PR, dj.R, n - a - x, c, d);
      q += 5;
      for (let n = 1; n <= 5; n++) aux[q++] = vs(0, 0, n, c, d);
    }
    const termS = term, Ws = solve(wasm, stS, term, dims, aux).out;
    progress && progress(2);
    // PSR目標。手持ち＝[PR][R][SR]（2枚目以降のPSRとPSR像は全部ベースに使う）
    dims = [C + 1, D + 1, 1, S + 1]; cells = dims[0] * dims[1] * (S + 1);
    term = new Float32Array(cells * 5); aux = new Float32Array(cells * 10); k = 0; q = 0;
    for (let c = 0; c <= C; c++) for (let d = 0; d <= D; d++) for (let s = 0; s <= S; s++) {
      for (let n = 1; n <= 5; n++) term[k++] = vp(VPk, n, s, c, d);
      for (let n = 1; n <= 5; n++) aux[q++] = vp(VP0, n, s, c, d);
      for (let n = 1; n <= 5; n++) aux[q++] = vs(0, 0, n, c, d);
    }
    const termP = term, Wp = solve(wasm, stP, term, dims, aux).out;
    progress && progress(3);
    // ガチャを1枠ずつ引いて、ステップごとの確率を出す（gacha_calc/build_tables.py と同じ）
    const ex = wasm.exports;
    ex.reset();
    const NP = 7 * (S + 1) * (C + 1) * (D + 1);
    const pP = ex.alloc(NP * 8), pPr = ex.alloc(32), pOut = ex.alloc(24), pWp = ex.alloc(Wp.length * 4), pWs = ex.alloc(Ws.length * 4),
      pTp = ex.alloc(Wp.length * 4), pTs = ex.alloc(Ws.length * 4);
    new Float32Array(ex.memory.buffer, pWp, Wp.length).set(Wp);
    new Float32Array(ex.memory.buffer, pWs, Ws.length).set(Ws);
    new Float32Array(ex.memory.buffer, pTp, Wp.length).set(termP);
    new Float32Array(ex.memory.buffer, pTs, Ws.length).set(termS);
    const start = [0, 0, 0, 0], AX = { PSR: 0, SR: 1, PR: 2, R: 3 };
    for (const x of job.extra || []) start[AX[x.rarity]] += x.n;
    new Float64Array(ex.memory.buffer, pP, NP).fill(0);
    new Float64Array(ex.memory.buffer, pP, NP)[((Math.min(start[0], 6) * (S + 1) + Math.min(start[1], S)) * (C + 1) + Math.min(start[2], C)) * (D + 1) + Math.min(start[3], D)] = 1;
    const L = job.steps.length, out = { LV40: [], SR45: [], PSR50: [] };
    // base＝旧カードなしを同じ表（1/255きざみに丸めた値）で計算したもの。ページ側で「正確な旧カードなしの値＋（out − base）」にして、丸めの誤差を打ち消す
    const base = { LV40: [], SR45: [], PSR50: [] };
    for (let st = 0; st < Math.max(90, 40 * L); st++) {
      const step = job.steps[job.loop ? st % L : Math.min(st, L - 1)];
      for (const slot of step.slots) {
        const pr = [0, 0, 0, 0];
        for (const r in slot.rarity) pr[AX[r]] = slot.rarity[r] / 100 * (slot.target === "pick" ? 1 : (slot.target === "only" ? 1 : job.share[r] / 100) / job.nch);
        new Float64Array(ex.memory.buffer, pPr, 4).set(pr);
        for (let i = 0; i < slot.n; i++) ex.pull(pP, pPr);
      }
      ex.eval_step(pP, pWp, pWs, dj.PSR, dj.SR, pOut);
      const o = new Float64Array(ex.memory.buffer, pOut, 3);
      out.LV40.push(o[0] * 100); out.SR45.push(o[1] * 100); out.PSR50.push(o[2] * 100);
      const done = o[1] >= .999 && o[2] >= .995 && (st + 1) % L === 0;
      ex.eval_step(pP, pTp, pTs, dj.PSR, dj.SR, pOut);
      const b = new Float64Array(ex.memory.buffer, pOut, 3);
      base.LV40.push(b[0] * 100); base.SR45.push(b[1] * 100); base.PSR50.push(b[2] * 100);
      if (done) break;
    }
    return { tables: out, base, Ws, Wp, moves: [stS.nMoves, stP.nMoves], tier: [stS.tier, stP.tier] };
  }
  root.GachaOld = { merge, graph, solve, plan, run };
  if (typeof importScripts === "function") {   // Web Worker として動くとき
    const cache = {};
    const get = (path) => cache[path] || (cache[path] = fetch(root.GachaOldBase + path).then((r) => { if (!r.ok) throw new Error(path); return r.arrayBuffer(); })
      .catch((err) => { delete cache[path]; throw err; }));
    root.onmessage = (ev) => {
      const job = ev.data;
      root.GachaOldBase = job.base;
      run(job, get, (p) => root.postMessage({ id: job.id, progress: p }))
        .then((r) => root.postMessage(Object.assign({ id: job.id }, r), r.Ws ? [r.Ws.buffer, r.Wp.buffer] : []))
        .catch((err) => root.postMessage({ id: job.id, error: String(err && err.message || err) }));
    };
  }
})(typeof self !== "undefined" ? self : globalThis);
