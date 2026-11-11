// デッキページの情報から、YouTube動画用のスライド（1920×1080 PNG）を1デッキにつき2枚作る。
//   1枚目：育成結果画像＋文章スペース／メイン・サポートデッキ画像（青・緑の縁）／メイン・サポートの表
//   2枚目：育成結果画像＋文章スペース／メイン・サポートデッキ画像／選手能力の画像＋動画のサムネイル／一番下は1行ぶんの空欄
// 表の数値はデッキページと同じ（docs/decks/<学園>/ を実際に開いて、deck.js の slotTable・supportTable で作る）。●☆の印は外す。
// 使い方: node youtube-slides/deck_slides.js <デッキ> [出力先フォルダ] [--thumb サムネイル画像]
//   <デッキ> は decks.js の画像名の後ろ（例：育成結果が result_roman_8 なら roman_8）
//   サムネイルは https://i.ytimg.com から読む。ネットで読めない環境では --thumb で画像ファイルを渡す（無ければ空の枠）
const {chromium} = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');

const args = process.argv.slice(2);
const ti = args.indexOf('--thumb');
const THUMB = ti >= 0 ? path.resolve(args.splice(ti, 2)[1]) : null;
const KEY = args[0];
const OUT = path.resolve(args[1] || path.join(__dirname, 'out'));
if (!KEY) { console.error('デッキを指定してください（例：roman_8）'); process.exit(1); }
const SCHOOL = KEY.replace(/_\d+$/, '');
const DOCS = path.join(__dirname, '..', 'docs');

// docs/ をそのまま配る小さなサーバー（data/chars.json を読むため file:// ではなく http で開く）
const TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml'};
const server = http.createServer((req, res) => {
  if (req.url.startsWith('/__thumb') && THUMB) { res.writeHead(200); return fs.createReadStream(THUMB).pipe(res); }
  let p = path.join(DOCS, decodeURIComponent(req.url.split('?')[0]));
  if (p.endsWith('/')) p += 'index.html';
  if (!p.startsWith(DOCS) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, {'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream'});
  fs.createReadStream(p).pipe(res);
});

const CSS = `
*{box-sizing:border-box;margin:0;padding:0}
body{width:1920px;height:1080px;overflow:hidden;background:#eaeeea;font-family:'M PLUS 1p',sans-serif;color:#14233a;position:relative}
.abs{position:absolute}
.result{left:48px;top:37px;height:146px;display:block}
.label{font-weight:900;font-size:82px;line-height:1;letter-spacing:2px;color:#fff;-webkit-text-stroke:14px var(--c);paint-order:stroke fill;filter:drop-shadow(0 4px 0 rgba(0,0,0,.25))}
.lmain{left:56px;top:215px;--c:#1a3cff}
.lsub{right:56px;top:215px;--c:#169a2c}
.deck{top:305px;display:flex;background:#fff}
.deck img{display:block;height:100%;width:auto}
.dmain{left:55px;border:8px solid #0a2cff}
.dsub{right:56px;border:8px solid #0d8a1f}
.tbl{top:592px;background:#fff;border-radius:4px;box-shadow:0 2px 10px rgba(0,0,0,.06);padding:4px 18px 6px}
table{border-collapse:collapse;width:100%}
th{font-weight:700;font-size:24px;color:#6b7684;text-align:left;padding:14px 10px 12px;border-bottom:2px solid #dfe3e8;white-space:nowrap}
td{font-weight:800;font-size:28px;height:56px;padding:0 10px;border-bottom:2px solid #e6e9ed;white-space:nowrap;vertical-align:middle}
tr:last-child td{border-bottom:0}
td.num{text-align:right}th.num{text-align:right}
td.rl{font-size:24px;color:#6b7684;font-weight:700}
td.name{font-weight:900}
.nick{font-size:.78em;color:#6b7684;font-weight:700;margin-right:2px}
td.memo{font-size:20px;line-height:1.35;color:#6b7684;font-weight:700}
.judge{display:inline-block;font-size:24px;font-weight:800;border-radius:6px;padding:2px 14px}
.judge.ok{background:#e3f4e6;color:#1d7a32}.judge.ng{background:#eef0f2;color:#6b7684}.judge.heal{background:#fbf0d2;color:#9a6b00}
.base{display:block;border-radius:4px}
.ability{left:55px;top:590px;display:block}
.thumb{right:56px;top:590px;width:634px;height:357px;background:#d9ded9;overflow:hidden}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
`;

(async () => {
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}/`;
  const opt = process.env.HTTPS_PROXY ? {proxy: {server: process.env.HTTPS_PROXY, bypass: '127.0.0.1,localhost'}} : {};
  const b = await chromium.launch(opt);
  const p = await b.newPage({viewport: {width: 1920, height: 1080}});
  await p.goto(`${base}decks/${SCHOOL}/`);
  await p.waitForFunction(() => typeof CHAR !== 'undefined' && Object.keys(CHAR).length > 0, null, {timeout: 30000});
  const info = await p.evaluate(key => {
    const d = DECKS[state.school].list.find(x => x.r === `result_${key}`);
    if (!d) return null;
    const clean = h => h.replace(/<span class="smark"[^>]*>●<\/span>/g, '').replace(/<span class="star"[^>]*>☆<\/span>/g, '')
      .replace(/​/g, '').replace(/<br>/g, '<br>');
    return {main: clean(slotTable(d.main, d.pos)), sub: clean(supportTable(d.sub, d.pos)), r: d.r, d: d.d, s: d.s, a: d.a, u: d.u, video: d.video};
  }, KEY);
  if (!info) { console.error(`${KEY} のデッキが decks.js にありません（育成結果画像の名前 result_${KEY} で探しています）`); process.exit(1); }
  const img = n => `${base}img/decks/${n}.jpg`;
  const size = async n => p.evaluate(src => new Promise(r => { const i = new Image(); i.onload = () => r([i.naturalWidth, i.naturalHeight]); i.src = src; }), img(n));
  const [mw, mh0] = await size(info.d), [sw, sh] = await size(info.s);
  // 下の端（アイテム枠の下の線）が切れているメイン画像は、切れた分の高さを下に足して表示する（管理人指示 2026-11-10）。
  // roman_1〜5 は roman_6〜8 より中身が6px下にずれて切り出されている。
  const MAIN_PAD = {roman_1: 6, roman_2: 6, roman_3: 6, roman_4: 6, roman_5: 6};
  const mpad = MAIN_PAD[KEY] || 0, mh = mh0 + mpad;
  // メインとサポートの画像を同じ高さに並べる（横幅 1810px に収まる最大、高さは最大 270px）
  const gap = 62, border = 16;
  // サポート画像は「合致」の帯まで入った高さ（幅386:高さ188）を基準にする。帯の無い画像（合致キャラなし）も同じ大きさで上に寄せ、下は空白（管理人指示 2026-11-10）
  const shFull = Math.max(sh, sw * 188 / 386);
  const H = Math.min(270, Math.floor((1809 - gap - 2 * border) / (mw / mh + sw / shFull)));
  const subW = Math.round(sw * H / shFull);
  const mainW = Math.round(mw * H / mh);
  const deckRow = `<div class="abs deck dmain" style="height:${H + border}px;align-items:flex-start;background:#f2fbfe"><img src="${img(info.d)}" style="width:${mainW}px;height:auto"></div>
    <div class="abs deck dsub" style="height:${H + border}px;align-items:flex-start"><img src="${img(info.s)}" style="width:${subW}px;height:auto"></div>`;
  const head = `<img class="abs result" src="${img(info.r)}">
    <div class="abs label lmain">メインデッキ</div><div class="abs label lsub">サポートデッキ</div>${deckRow}`;
  const doc = body => `<!doctype html><html lang="ja"><head><meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=M+PLUS+1p:wght@700;800;900&display=swap" rel="stylesheet">
    <style>${CSS}</style></head><body>${body}</body></html>`;
  const s1 = doc(head + `<div class="abs tbl" style="left:55px;width:1000px">${info.main}</div>
    <div class="abs tbl tsub" style="right:56px;width:760px">${info.sub}</div>`
    + (info.u ? `<img class="abs base" src="${img(info.u)}">` : ''));   // サポートの表の下に基礎上限の画像（管理人指示 2026-11-10）
  const thumbSrc = THUMB ? `${base}__thumb` : (/^[\w-]{11}$/.test(info.video || '') ? `https://i.ytimg.com/vi/${info.video}/maxresdefault.jpg` : '');
  const s2 = doc(head + (info.a ? `<img class="abs ability" src="${img(info.a)}" style="width:1113px;height:357px;object-fit:contain;object-position:left top">` : '')
    + `<div class="abs thumb">${thumbSrc ? `<img src="${thumbSrc}" onerror="if(!this.dataset.hq&&/maxresdefault/.test(this.src)){this.dataset.hq=1;this.src=this.src.replace('maxresdefault','hqdefault')}else this.remove()">` : ''}</div>`);

  fs.mkdirSync(OUT, {recursive: true});
  const fit = async () => p.evaluate(async () => {
    await document.fonts.ready;
    // 表が下や横にはみ出す時は、文字を小さくして収める
    document.querySelectorAll('.tbl').forEach(t => {
      const tb = t.querySelector('table'), r = t.getBoundingClientRect();
      const z = Math.min(1, (t.clientWidth - 36) / tb.scrollWidth, (1074 - r.top) / r.height);
      if (z < 1) tb.style.zoom = z;
    });
    // 基礎上限の画像：サポートの表のすぐ下に、残りの高さと表の幅に収まる大きさで置く
    const bs = document.querySelector('.base'), ts = document.querySelector('.tsub');
    if (bs && ts) {
      await bs.decode().catch(() => {});
      const r = ts.getBoundingClientRect(), top = r.bottom + 18, h = Math.min(1062 - top, r.width * bs.naturalHeight / bs.naturalWidth);
      Object.assign(bs.style, {top: top + 'px', height: h + 'px', width: 'auto', right: '56px'});
    }
  });
  const shots = [];
  for (const [i, html] of [[1, s1], [2, s2]]) {
    await p.goto(base + 'index.html');            // 同じ場所（http）から画像を読めるようにしてから中身を入れ替える
    await p.setContent(html, {waitUntil: 'networkidle'});
    await fit();
    const out = path.join(OUT, `deck_${KEY}_${i}.png`);
    await p.screenshot({path: out});
    shots.push(out);
  }
  const thumbOk = await p.evaluate(() => !!document.querySelector('.thumb img')?.naturalWidth);
  await b.close(); server.close();
  console.log(shots.join('\n'));
  if (!thumbOk) console.log(info.video === 'なし' ? '※ このデッキは動画が「なし」なので、2枚目のサムネイル欄は空です' : '※ サムネイルを読めなかったので、2枚目のサムネイル欄は空です（--thumb で画像を渡せます）');
})();
