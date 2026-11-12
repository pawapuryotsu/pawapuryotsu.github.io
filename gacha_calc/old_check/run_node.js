// 出力は「旧カードなしからの上がり幅（ポイント）」を周ごとに。
// 旧バージョンつきの計算（src/assets/gacha_old.js）を Node で動かす（検算用）。
//   node gacha_calc/old_check/run_node.js <ガチャid> '<旧カード [[ランク(0=R..3=PSR), +いくつ, 枚数],…]>' [博士像 PSR,SR,PR,R]
const fs = require("fs"), path = require("path");
const root = path.join(__dirname, "..", "..");
require(path.join(root, "src/assets/gacha_old.js"));
const g = JSON.parse(fs.readFileSync(path.join(root, "src/gacha", process.argv[2] + ".json"), "utf8"));
const old = JSON.parse(process.argv[3] || "[]").map(([r, l, n]) => ({ r, l, n: n || 1 }));
const dj = (process.argv[4] || "0,0,0,0").split(",").map(Number);
const get = async (p) => { const b = fs.readFileSync(path.join(root, "src/assets", p)); return b.buffer.slice(b.byteOffset, b.byteOffset + b.length); };
const t0 = Date.now();
GachaOld.run({ steps: g.steps, loop: g.loop, share: g.share, nch: (g.charas || [0]).length, extra: g.extra || [], old, dj: { PSR: dj[0], SR: dj[1], PR: dj[2], R: dj[3] }, KL: 10 }, get).then((r) => {
  if (r.error) return console.log("error", r.error);
  const L = g.steps.length;
  console.log("合成の手の数（SR目標・PSR目標）", r.moves.join(" "));
  for (const k of ["LV40", "SR45", "PSR50"]) console.log(k, r.tables[k].map((v, i) => v - r.base[k][i]).filter((_, i) => i % L === L - 1).slice(0, 12).map((v) => v.toFixed(2)).join(" "));
  console.log("ms", Date.now() - t0);
});
