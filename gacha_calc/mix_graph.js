// 別バージョン（通常版など）のカードを持っているときの「合成の手の一覧」を、src/assets/gacha_old.js と同じ作り方で書き出す。
// mix.py から呼ばれる：node mix_graph.js '<手持ちの一覧のJSON>' 出力ファイル
//   手持ち＝[R, PR, SR, PSR] の枚数（どれも +0）。出力＝手持ちごと・目標ごと（2＝SR目標、3＝PSR目標）の配列（old.c の solve にそのまま渡す形）
const path = require("path"), fs = require("fs");
require(path.join(__dirname, "..", "src", "assets", "gacha_old.js"));
const G = globalThis.GachaOld;
const out = [];
for (const pool of JSON.parse(process.argv[2])) {
  const old = [];
  pool.forEach((n, r) => { for (let i = 0; i < n; i++) old.push({ r, v: 1, l: 0 }); });
  const row = { pool };
  for (const goal of [2, 3]) {
    const st = G.plan(goal, old);
    if (!st) throw new Error("too_many " + JSON.stringify(pool));
    const NS = st.length;
    const size = st.map((s) => s.P.length + (s.t >= 0 ? 1 : 0));
    const order = [...Array(NS).keys()].sort((a, b) => size[a] - size[b]);
    const mStart = [], mNeed = [], oStart = [], oP = [], oJ = [], oD = [], aS = [], aK = [], aU = [], aJ = [];
    for (let i = 0; i < NS; i++) {
      aS.push(aK.length);
      for (const [kind, up, j] of st[i].allin) { aK.push(kind); aU.push(up); aJ.push(j * 5); }
      mStart.push(mNeed.length);
      for (const m of st[i].moves) { mNeed.push(m.need); oStart.push(oP.length); for (const [p, j, d] of m.outs) { oP.push(p); oJ.push(j * 5); oD.push(d); } }
    }
    mStart.push(mNeed.length); oStart.push(oP.length); aS.push(aK.length);
    row[goal] = { NS, tier: st.tier, order, mStart, mNeed, oStart, oP, oJ, oD, aS, aK, aU, aJ };
  }
  out.push(row);
}
fs.writeFileSync(process.argv[3], JSON.stringify(out));
