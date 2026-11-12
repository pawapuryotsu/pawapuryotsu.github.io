// ガチャ記事の「周回ごとの確率」の表と「引いてみる」シミュレータ。データはページ内の #gdata（JSON）。
// 博士像ありの表は assets/gacha_t/<id>.bin、手持ち→達成確率の表は assets/gacha_v/*.bin（gacha_calc/build_tables.py が作る）。
// 旧バージョンの手持ちを入れたとき（json の "old_ver"）は、assets/gacha_old.js（Web Worker）がその場で計算する。
(function () {
  const G = JSON.parse(document.getElementById("gdata").textContent);
  const root = document.body.dataset.root || "./";
  const $ = (id) => document.getElementById(id);
  const RS = ["PSR", "SR", "PR", "R"];
  const NCH = G.charas.length;   // 出現率アップキャラの人数（only・share の枠は人数で等分。pick＝選択券は必ず目当てキャラ）
  let CH = G.charas[0];          // 表示中のキャラ（複数キャラのガチャはボタンで切り替え）
  let T = G.tables.SR45.length;
  const L = G.steps.length, KS1 = G.tables.KS + 1, KL1 = G.tables.KL + 1, K3 = KS1 * KL1 * KL1;   // 博士像の枚数の上限（PSR・SR像と PR・R像）
  const SB = 24, CB = 34, DB = 60;   // 手持ち→達成確率の表の大きさ（build_tables.py の S, C, D と同じ値。超えた枚数は上限と同じ扱い）
  const DJ = { PSR: 0, SR: 0, PR: 0, R: 0 };   // 使う博士像の枚数
  const bin = (path, type, done) => fetch(root + "assets/" + path).then((r) => { if (!r.ok) throw 0; return r.arrayBuffer(); }).then((b) => done(new type(b)));
  const stepOf = (i) => G.steps[G.loop ? i % L : Math.min(i, L - 1)];
  function used(st) { let p = 0, s = 0; for (let i = 0; i < st; i++) { p += stepOf(i).pulls; s += stepOf(i).cost; } return [p, s]; }
  function label(st) {
    if (!G.loop) return st + "ステップ";
    const l = Math.floor(st / L), r = st % L;
    return (l ? '<span class="cp-nw">' + l + "周</span>" : "") + (r ? (l ? "＋" : "") + '<span class="cp-nw">' + r + "ステップ</span>" : "");
  }

  // ---- 旧バージョンの手持ち（入力欄があるガチャだけ） ----
  // OLD.pool＝計算に使う旧カード [{r（0=R 1=PR 2=SR 3=PSR）, l（+いくつ）, n（枚数）}]。OLD.res＝計算結果（まだなら null）
  const OLD = { pool: [], res: null, job: 0, worker: null };
  const oldOn = () => OLD.pool.length > 0 && !CH.both;
  function oldStatus(t, err) { const el = $("g-olds"); if (el) { el.textContent = t; el.classList.toggle("g-err", !!err); } }
  function runOld() {
    OLD.res = null;
    const id = ++OLD.job;
    if (!oldOn()) { oldStatus(OLD.pool.length ? "「2人とも」では旧バージョンの手持ちは使いません。" : ""); renderTable(); draw(); return; }
    oldStatus("計算中…（数秒〜数十秒かかります）");
    renderTable(); draw();
    try {
      if (!OLD.worker) {
        OLD.worker = new Worker(root + "assets/gacha_old.js?v=" + G.old_v);
        OLD.worker.onmessage = (ev) => {
          const m = ev.data;
          if (m.id !== OLD.job || m.progress) return;
          if (m.error) { oldStatus(m.error === "too_many" ? "旧バージョンのカードの種類・枚数が多すぎて計算できません。影響の小さいカード（Rなど）から減らしてください。" : "計算できませんでした。通信状況を確認して、もう一度「計算する」を押してください。", true); return; }
          OLD.res = m;
          const names = ["R", "PR", "SR", "PSR"];
          oldStatus("旧バージョン（" + OLD.pool.map((c) => names[c.r] + "+" + c.l + "×" + c.n).join("・") + "）を使う前提の確率を表示中です（1%きざみ）。"
            + (m.tier[0] > 1 || m.tier[1] > 3 ? "カードが多いため、合成の順番を調べる範囲をせばめて計算しました（実際より低めに出やすくなります）。" : ""));
          renderTable(); draw();
        };
        OLD.worker.onerror = () => { OLD.worker = null; oldStatus("計算できませんでした。もう一度「計算する」を押してください。", true); };
      }
      OLD.worker.postMessage({ id, base: new URL(root + "assets/", location.href).href, steps: G.steps, loop: !!G.loop, share: G.share, nch: NCH,
        extra: CH.extra || [], old: OLD.pool, dj: Object.assign({}, DJ), KL: G.tables.KL });
    } catch (e) { oldStatus("このブラウザでは旧バージョンの計算ができません。", true); }
  }
  function readOld() {
    const pool = [];
    document.querySelectorAll("[data-old]").forEach((el) => {
      const n = Math.max(0, Math.min(9, Math.floor(+el.value || 0)));
      el.value = n || "";
      const [r, l] = el.dataset.old.split("_").map(Number);
      if (n) pool.push({ r, l, n });
    });
    OLD.pool = pool;
    runOld();
  }
  if ($("g-oldgo")) {
    $("g-oldgo").onclick = readOld;
    $("g-oldclr").onclick = () => { document.querySelectorAll("[data-old]").forEach((el) => { el.value = ""; }); readOld(); };
  }

  // ---- 周回ごとの確率 ----
  let TB = null, tbReq = false, goal = "SR45";
  function table(g) {   // ステップごとの確率（%）。まだ計算・読み込みが終わっていなければ null
    const t = table0(g);
    if (!oldOn()) return t;
    if (!OLD.res || !t) return null;
    // 旧バージョン込み：正確な「旧カードなし」の値に、旧カードで上がる分（同じ丸めの表で計算した差）を足す
    const o = OLD.res.tables[g], b = OLD.res.base[g];
    return o.slice(0, t.length).map((v, i) => t[i] >= 100 ? 100 : Math.min(99.99, Math.max(t[i], t[i] + v - b[i])));
  }
  function table0(g) {
    const i3 = (DJ.SR * KL1 + DJ.PR) * KL1 + DJ.R;
    if (CH.both) return G.tables[g];   // 「2人とも」は博士像なしの表だけ
    if (i3 === 0 && (g !== "PSR50" || DJ.PSR === 0)) return G.tables[g];
    if (!TB) {
      if (!tbReq) {
        tbReq = true;
        const want = CH;
        bin("gacha_t/" + G.id + (want.key ? "_" + want.key : "") + ".bin", Uint16Array, (a) => { if (CH !== want) return; TB = a; renderTable(); }).catch(() => { if (CH === want) tbReq = false; });
      }
      return null;
    }
    const off = (g === "SR45" ? i3 : g === "LV40" ? K3 + i3 : 2 * K3 + DJ.PSR * K3 + i3) * T;
    return Array.from(TB.subarray(off, off + T), (v) => v / 655.35);
  }
  // 旧バージョン込みのときは1%きざみ（合成の順番を全部は調べていない計算なので、細かい数字は出さない）
  const pct = (v) => v >= 100 ? "100%" : oldOn() ? (v >= 99.5 ? "ほぼ100%" : v < 0.5 ? "1%未満" : "約" + Math.round(v) + "%")
    : v >= 99.95 ? "ほぼ100%" : (Math.round(v * 10) / 10).toFixed(1) + "%";
  const pct0 = (v) => v >= 100 ? "100%" : v >= 99.95 ? "ほぼ100%" : (Math.round(v * 10) / 10).toFixed(1) + "%";   // 「引ける確率」は旧バージョンに関係ない
  const cell = (t, i) => t ? `<td class="${t[i] >= 50 ? "g-hit" : ""}">${pct(t[i])}</td>` : "<td>…</td>";
  function renderTable() {
    const ts = ["LV40", "SR45", "PSR50"].map(table);
    let h = "";
    const TT = Math.min(T, ...ts.map((t) => t ? t.length : T));
    for (let n = 1; n * L <= TT; n++) {
      if (n > 3 && ts.every((t) => t && t[(n - 1) * L - 1] >= 99.9)) break;
      const [p, s] = used(n * L);
      h += `<tr><td>${n}周<br><small><span class="cp-nw">${p}連</span>・<span class="cp-nw">石${s}個</span></small></td>${ts.map((t) => cell(t, n * L - 1)).join("")}</tr>`;
    }
    $("g-tbl").innerHTML = h;
    const gs = [G.tables.gotSR, G.tables.gotPSR];
    h = "";
    // ステップごと。PSRが1枚以上＝100%（確定）になった行まで。100%にならなければ90%以上になった行まで（管理人 2026-11-12）
    const gp = G.tables.gotPSR;
    let last = gp.findIndex((v) => v >= 100);
    if (last < 0) last = gp.findIndex((v) => v >= 90);
    if (last < 0) last = T - 1;
    for (let i = 0; i <= last; i++) {
      const name = G.loop ? `<span class="cp-nw">${Math.floor(i / L) + 1}周目</span> <span class="cp-nw">${stepOf(i).name}</span>` : stepOf(i).name;
      h += `<tr${G.loop && i > 0 && i % L === 0 ? ' class="g-lp"' : ""}><td class="g-l">${name}</td><td>${used(i + 1)[1]}個</td>${gs.map((t) => `<td>${pct0(t[i])}</td>`).join("")}</tr>`;
    }
    $("g-tbl2").innerHTML = h;
    const t = table(goal);
    for (const x of [50, 80, 90]) {
      const st = t ? t.findIndex((v) => v >= x) + 1 : 0;
      if (st === 0) { $("g-p" + x).innerHTML = t ? "—" : "…"; $("g-p" + x + "s").textContent = ""; continue; }
      const [p, s] = used(st);
      $("g-p" + x).innerHTML = label(st);
      $("g-p" + x + "s").innerHTML = `<span class="cp-nw">${p}連</span> <span class="cp-nw">石${s}個</span>`;
    }
    document.querySelectorAll("[data-goal]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.goal === goal));
  }
  document.querySelectorAll("[data-goal]").forEach((b) => (b.onclick = () => { goal = b.dataset.goal; renderTable(); }));

  // ---- 引いてみる ----
  function pullSlot(slot) {
    let u = Math.random() * 100, c = 0;
    for (const r of RS) {
      if (!(r in slot.rarity)) continue;
      c += slot.rarity[r];
      if (u < c) {
        if (slot.target === "pick") return r;
        return Math.random() * NCH < 1 && (slot.target === "only" || Math.random() * 100 < G.share[r]) ? r : null;
      }
    }
    return null;
  }
  function pullStep(i) { const out = []; for (const s of stepOf(i).slots) for (let k = 0; k < s.n; k++) { const r = pullSlot(s); if (r) out.push(r); } return out; }

  // 手持ち→達成確率（一番成功率が高い順番で合成したとき。事前に全パターンを計算した表を読む。0〜255）
  let VS = null, vsReq = false;
  const VP = {};
  const u255 = (v) => v >= 1 ? 255 : v <= 0 ? 0 : Math.min(254, Math.max(1, Math.round(v * 255)));
  function pSold(h, N, psr) {   // 旧バージョン込み（OLD.res.Ws＝[PR][R][PSR 0..4][ベース以外のSR 0..4][あと何段階-1]）
    if (!OLD.res) return null;
    const n = N - DJ.SR, x = h.SR - 1;
    if (n <= 0 || psr + x >= n) return 255;
    return u255(OLD.res.Ws[(((Math.min(h.PR, CB) * (DB + 1) + Math.min(h.R, DB)) * 5 + psr) * 5 + x) * 5 + n - 1]);
  }
  function pS(h, N, free) {   // SRをあとN段階。free＝確定で+1できる枚数（2枚目以降のSRなど）
    if (h.SR === 0) return 0;
    if (oldOn()) return pSold(h, N, free - (h.SR - 1));
    const n = N - free - DJ.SR;
    if (n <= 0) return 255;
    if (!VS) {
      if (!vsReq) { vsReq = true; bin("gacha_v/sr.bin", Uint8Array, (a) => { VS = a; draw(); }).catch(() => { vsReq = false; }); }
      return null;
    }
    return VS[(((DJ.PR * KL1 + DJ.R) * 5 + n - 1) * (CB + 1) + Math.min(h.PR, CB)) * (DB + 1) + Math.min(h.R, DB)];
  }
  const pSR45 = (h) => pS(h, 5, h.SR - 1 + h.PSR);
  const pLV40 = (h) => h.PSR > 0 ? 255 : pS(h, 3, h.SR - 1);
  function pPSR50(h) {
    if (h.PSR === 0) return 0;
    const n = 5 - (h.PSR - 1) - DJ.PSR;
    if (n <= 0) return 255;
    if (oldOn()) return OLD.res ? u255(OLD.res.Wp[((Math.min(h.PR, CB) * (DB + 1) + Math.min(h.R, DB)) * (SB + 1) + Math.min(h.SR, SB)) * 5 + n - 1]) : null;
    const k = DJ.SR + "_" + DJ.PR + "_" + DJ.R;
    if (!(k in VP)) { VP[k] = null; bin("gacha_v/p" + k + ".bin", Uint8Array, (a) => { VP[k] = a; draw(); }).catch(() => { delete VP[k]; }); }
    if (!VP[k]) return null;
    return VP[k][(((n - 1) * (SB + 1) + Math.min(h.SR, SB)) * (CB + 1) + Math.min(h.PR, CB)) * (DB + 1) + Math.min(h.R, DB)];
  }

  let H, st, log;
  function reset() {
    const EX = CH.extra || [];   // ガチャ以外で手に入る分（イベント報酬など）。最初から手持ちに入れる
    H = { PSR: 0, SR: 0, PR: 0, R: 0 }; st = 0; log = [];
    for (const x of EX) { H[x.rarity] += x.n; log.push(`${x.label}：` + Array(x.n).fill(`<span class="g-${x.rarity}">${x.rarity}</span>`).join(" ")); }
    draw();
  }
  function bar(id, v) {
    $(id).textContent = v === null ? "計算中…" : v === 0 ? "0%" : v === 255 ? "100%" : v < 3 ? "1%未満" : v > 252 ? "99%以上" : Math.round(v / 2.55) + "%";
    $(id + "b").style.width = (v || 0) / 2.55 + "%";
  }
  function draw() {
    if (!H) return;
    const [p, s] = used(st);
    $("g-pulls").textContent = p + "連";
    $("g-stones").textContent = s + "個";
    $("g-next").textContent = G.loop ? `${Math.floor(st / L) + 1}周目 ${stepOf(st).name}` : stepOf(st).name;
    for (const r of RS) $("g-c" + r).textContent = H[r];
    bar("g-vlv", pLV40(H));
    bar("g-vsr", pSR45(H));
    bar("g-vpsr", pPSR50(H));
    $("g-log").innerHTML = log.slice(-60).reverse().join("<br>");
  }
  document.querySelectorAll("[data-pull]").forEach((b) => (b.onclick = () => {
    for (let i = 0; i < +b.dataset.pull; i++) {
      const r = pullStep(st);
      r.forEach((k) => H[k]++);
      log.push(`${G.loop ? Math.floor(st / L) + 1 + "周目 " : ""}${stepOf(st).name}：` + (r.length ? r.map((k) => `<span class="g-${k}">${k}</span>`).join(" ") : `${CH.chara}なし`));
      st++;
    }
    draw();
  }));
  $("g-reset").onclick = reset;
  // キャラの切り替え（複数キャラのガチャ）。表・文・シミュレータをそのキャラの分にする
  function setChara(k) {
    CH = G.charas.find((c) => c.key === k) || G.charas[0];
    G.tables = CH.tables; T = G.tables.SR45.length; TB = null; tbReq = false;
    document.querySelectorAll("[data-ch]").forEach((el) => { el.hidden = el.dataset.ch !== CH.key; });
    document.querySelectorAll("[data-nb]").forEach((el) => { el.hidden = !!CH.both; });   // シミュレータは1人ずつ
    document.querySelectorAll("[data-chb]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.chb === CH.key));
    renderTable();
    reset();
    runOld();
  }
  document.querySelectorAll("[data-chb]").forEach((b) => (b.onclick = () => setChara(b.dataset.chb)));
  document.querySelectorAll("[data-chb]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.chb === CH.key));
  // 博士像の枚数は、画面の選択欄の値をそのまま使う（ブラウザの「戻る」で選択欄だけ復元されてもずれないように）
  function syncDJ() { document.querySelectorAll("[data-dj]").forEach((el) => { DJ[el.dataset.dj] = +el.value || 0; }); renderTable(); draw(); runOld(); }
  document.querySelectorAll("[data-dj]").forEach((el) => (el.onchange = syncDJ));
  window.addEventListener("pageshow", syncDJ);
  reset();
  syncDJ();
})();
