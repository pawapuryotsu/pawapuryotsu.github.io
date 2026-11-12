// ガチャ記事の「周回ごとの確率」の表と「引いてみる」シミュレータ。データはページ内の #gdata（JSON）。
// 博士像ありの表は assets/gacha_t/<id>.bin、手持ち→達成確率の表は assets/gacha_v/*.bin（gacha_calc/build_tables.py が作る）。
(function () {
  const G = JSON.parse(document.getElementById("gdata").textContent);
  const root = document.body.dataset.root || "./";
  const $ = (id) => document.getElementById(id);
  const RS = ["PSR", "SR", "PR", "R"];
  const L = G.steps.length, T = G.tables.SR45.length, K1 = G.tables.K + 1, K3 = K1 * K1 * K1;
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

  // ---- 周回ごとの確率 ----
  let TB = null, tbReq = false, goal = "SR45";
  function table(g) {   // ステップごとの確率（%）。博士像ありの表がまだ読めていなければ null
    const i3 = (DJ.SR * K1 + DJ.PR) * K1 + DJ.R;
    if (i3 === 0 && (g !== "PSR50" || DJ.PSR === 0)) return G.tables[g];
    if (!TB) {
      if (!tbReq) { tbReq = true; bin("gacha_t/" + G.id + ".bin", Uint16Array, (a) => { TB = a; renderTable(); }).catch(() => { tbReq = false; }); }
      return null;
    }
    const off = (g === "SR45" ? i3 : g === "LV40" ? K3 + i3 : 2 * K3 + DJ.PSR * K3 + i3) * T;
    return Array.from(TB.subarray(off, off + T), (v) => v / 655.35);
  }
  const pct = (v) => v >= 100 ? "100%" : v >= 99.95 ? "ほぼ100%" : (Math.round(v * 10) / 10).toFixed(1) + "%";
  const cell = (t, i) => t ? `<td class="${t[i] >= 50 ? "g-hit" : ""}">${pct(t[i])}</td>` : "<td>…</td>";
  function renderTable() {
    const ts = ["LV40", "SR45", "PSR50"].map(table);
    let h = "";
    for (let n = 1; n * L <= T; n++) {
      if (n > 3 && ts.every((t) => t && t[(n - 1) * L - 1] >= 99.9)) break;
      const [p, s] = used(n * L);
      h += `<tr><td>${n}周<br><small><span class="cp-nw">${p}連</span>・<span class="cp-nw">石${s}個</span></small></td>${ts.map((t) => cell(t, n * L - 1)).join("")}</tr>`;
    }
    $("g-tbl").innerHTML = h;
    const gs = [G.tables.gotSR, G.tables.gotPSR];
    h = "";
    for (let i = 0; i < T; i++) {   // ステップごと
      const name = G.loop ? `<span class="cp-nw">${Math.floor(i / L) + 1}周目</span> <span class="cp-nw">${stepOf(i).name}</span>` : stepOf(i).name;
      h += `<tr class="g-s${(i % L) % 4 + 1}"><td class="g-l">${name}</td><td>${used(i + 1)[1]}個</td>${gs.map((t) => cell(t, i)).join("")}</tr>`;
      if (G.tables.gotSR[i] >= 99.95) break;   // SRがほぼ100%になったステップまで出す（管理人の希望）
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
      if (u < c) return slot.target === "only" || Math.random() * 100 < G.share[r] ? r : null;
    }
    return null;
  }
  function pullStep(i) { const out = []; for (const s of stepOf(i).slots) for (let k = 0; k < s.n; k++) { const r = pullSlot(s); if (r) out.push(r); } return out; }

  // 手持ち→達成確率（一番成功率が高い順番で合成したとき。事前に全パターンを計算した表を読む。0〜255）
  let VS = null, vsReq = false;
  const VP = {};
  function pS(h, N, free) {   // SRをあとN段階。free＝確定で+1できる枚数（2枚目以降のSRなど）
    if (h.SR === 0) return 0;
    const n = N - free - DJ.SR;
    if (n <= 0) return 255;
    if (!VS) {
      if (!vsReq) { vsReq = true; bin("gacha_v/sr.bin", Uint8Array, (a) => { VS = a; draw(); }).catch(() => { vsReq = false; }); }
      return null;
    }
    return VS[(((DJ.PR * K1 + DJ.R) * 5 + n - 1) * (CB + 1) + Math.min(h.PR, CB)) * (DB + 1) + Math.min(h.R, DB)];
  }
  const pSR45 = (h) => pS(h, 5, h.SR - 1 + h.PSR);
  const pLV40 = (h) => h.PSR > 0 ? 255 : pS(h, 3, h.SR - 1);
  function pPSR50(h) {
    if (h.PSR === 0) return 0;
    const n = 5 - (h.PSR - 1) - DJ.PSR;
    if (n <= 0) return 255;
    const k = "" + DJ.SR + DJ.PR + DJ.R;
    if (!(k in VP)) { VP[k] = null; bin("gacha_v/p" + k + ".bin", Uint8Array, (a) => { VP[k] = a; draw(); }).catch(() => { delete VP[k]; }); }
    if (!VP[k]) return null;
    return VP[k][(((n - 1) * (SB + 1) + Math.min(h.SR, SB)) * (CB + 1) + Math.min(h.PR, CB)) * (DB + 1) + Math.min(h.R, DB)];
  }

  let H, st, log;
  function reset() { H = { PSR: 0, SR: 0, PR: 0, R: 0 }; st = 0; log = []; draw(); }
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
      log.push(`${G.loop ? Math.floor(st / L) + 1 + "周目 " : ""}${stepOf(st).name}：` + (r.length ? r.map((k) => `<span class="g-${k}">${k}</span>`).join(" ") : `${G.chara}なし`));
      st++;
    }
    draw();
  }));
  $("g-reset").onclick = reset;
  // 博士像の枚数は、画面の選択欄の値をそのまま使う（ブラウザの「戻る」で選択欄だけ復元されてもずれないように）
  function syncDJ() { document.querySelectorAll("[data-dj]").forEach((el) => { DJ[el.dataset.dj] = +el.value || 0; }); renderTable(); draw(); }
  document.querySelectorAll("[data-dj]").forEach((el) => (el.onchange = syncDJ));
  window.addEventListener("pageshow", syncDJ);
  reset();
  syncDJ();
})();
