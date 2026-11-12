// ガチャ記事の「周回ごとの完成確率」の切り替えと「引いてみる」シミュレータ。データはページ内の #gdata（JSON）。
(function () {
  const G = JSON.parse(document.getElementById("gdata").textContent);
  const root = document.body.dataset.root || "./";
  const $ = (id) => document.getElementById(id);
  const L = G.steps.length;
  const stepOf = (i) => G.steps[G.loop ? i % L : Math.min(i, L - 1)];
  function used(st) { let p = 0, s = 0; for (let i = 0; i < st; i++) { p += stepOf(i).pulls; s += stepOf(i).cost; } return [p, s]; }
  function label(st) {
    if (!G.loop) return st + "ステップ";
    const l = Math.floor(st / L), r = st % L;
    return (l ? '<span class="cp-nw">' + l + "周</span>" : "") + (r ? (l ? "＋" : "") + '<span class="cp-nw">' + r + "ステップ</span>" : "");
  }

  // ---- 周回ごとの完成確率 ----
  function renderTable(goal) {
    const t = G.tables[goal];
    let h = "";
    for (let n = 1; n * L <= t.length; n++) {
      const v = t[n * L - 1];
      if (n > 3 && t[(n - 1) * L - 1] >= 99.9) break;
      const [p, s] = used(n * L);
      h += `<tr><td>${n}周</td><td>${p}連</td><td>${s}個</td><td class="${v >= 50 ? "g-hit" : ""}">${v >= 99.95 ? "ほぼ100" : v.toFixed(1)}%</td></tr>`;
    }
    $("g-tbl").innerHTML = h;
    for (const x of [50, 80, 90]) {
      const st = t.findIndex((v) => v >= x) + 1;
      const el = $("g-p" + x);
      if (!el) continue;
      if (st === 0) { el.innerHTML = "—"; $("g-p" + x + "s").textContent = ""; continue; }
      const [p, s] = used(st);
      el.innerHTML = label(st);
      $("g-p" + x + "s").textContent = `${p}連・石${s}個`;
    }
    document.querySelectorAll("[data-goal]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.goal === goal));
  }
  document.querySelectorAll("[data-goal]").forEach((b) => (b.onclick = () => renderTable(b.dataset.goal)));
  renderTable("SR45");

  // ---- 引いてみる ----
  const RS = ["PSR", "SR", "PR", "R"];
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

  // SR Lv45：手持ちを一番成功率が高い順番で合成したときの完成確率（全パターン）
  const LOW = [0.3, 0.33, 0.36, 0.39, 0.42], memo = new Map();
  function V(n, c0, t, d0, u) {
    if (n <= 0) return 1;
    const key = n + "," + c0 + "," + t + "," + d0 + "," + u;
    if (memo.has(key)) return memo.get(key);
    let b = 0;
    const lf = (lv, c, tt, d, uu) => lv === 5 ? 0.45 * V(n - 2, c, tt, d, uu) + 0.55 * V(n - 1, c, tt, d, uu) : LOW[lv] * V(n - 1, c, tt, d, uu) + (1 - LOW[lv]) * V(n, c, tt, d, uu);
    if (c0 > 0) b = Math.max(b, lf(0, c0 - 1, t, d0, u));
    if (t > 0) b = Math.max(b, lf(t, c0, 0, d0, u));
    if (c0 > 0 && t > 0 && t < 5) b = Math.max(b, V(n, c0 - 1, t + 1, d0, u));
    if (c0 > 1 && t === 0) b = Math.max(b, V(n, c0 - 2, 1, d0, u));
    const r2 = (lv, c0n, d0n, un) => {
      let base, cc;
      if (t > 0) { base = t; cc = c0n; } else if (c0n > 0) { base = 0; cc = c0n - 1; } else return 0;
      const res = (g) => base + g > 0 ? V(n, cc, Math.min(5, base + g), d0n, un) : V(n, cc + 1, 0, d0n, un);
      return lv === 5 ? 0.45 * res(2) + 0.55 * res(1) : LOW[lv] * res(1) + (1 - LOW[lv]) * res(0);
    };
    if (t < 5) { if (d0 > 0) b = Math.max(b, r2(0, c0, d0 - 1, u)); if (u > 0) b = Math.max(b, r2(u, c0, d0, 0)); }
    if (d0 > 0 && u > 0 && u < 5) b = Math.max(b, V(n, c0, t, d0 - 1, u + 1));
    if (d0 > 1 && u === 0) b = Math.max(b, V(n, c0, t, d0 - 2, 1));
    memo.set(key, b);
    return b;
  }
  const pSR = (h) => h.SR === 0 ? 0 : V(5 - (h.SR + h.PSR - 1), Math.min(h.PR, 34), 0, Math.min(h.R, 60), 0);
  // PSR Lv50：事前に全パターンを計算した表（assets/gacha_vpsr.bin）
  let VP = null;
  fetch(root + "assets/gacha_vpsr.bin").then((r) => r.arrayBuffer()).then((b) => { VP = new Uint8Array(b); draw(); }).catch(() => {});
  function pPSR(h) {
    if (h.PSR === 0) return 0;
    const n = 5 - (h.PSR - 1);
    if (n <= 0) return 1;
    if (!VP) return null;
    return VP[(((n - 1) * 25 + Math.min(h.SR, 24)) * 35 + Math.min(h.PR, 34)) * 61 + Math.min(h.R, 60)] / 255;
  }

  let H, st, log;
  function reset() { H = { PSR: 0, SR: 0, PR: 0, R: 0 }; st = 0; log = []; draw(); }
  function bar(id, v) { $(id).textContent = v === null ? "計算中…" : (v * 100).toFixed(1) + "%"; $(id + "b").style.width = (v || 0) * 100 + "%"; }
  function draw() {
    const [p, s] = used(st);
    $("g-pulls").textContent = p + "連";
    $("g-stones").textContent = s + "個";
    $("g-next").textContent = G.loop ? `${Math.floor(st / L) + 1}周目 ${stepOf(st).name}` : stepOf(st).name;
    for (const r of RS) $("g-c" + r).textContent = H[r];
    bar("g-vsr", pSR(H));
    bar("g-vpsr", pPSR(H));
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
  reset();
})();
