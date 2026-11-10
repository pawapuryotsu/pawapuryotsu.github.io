// make_slides.py から呼ばれる：HTMLを 1920×1080 のPNGにする
const {chromium} = require('playwright');
const jobs = require(process.argv[2]);
(async () => {
  const opt = process.env.HTTPS_PROXY ? {proxy: {server: process.env.HTTPS_PROXY}} : {};
  const b = await chromium.launch(opt);
  const p = await b.newPage({viewport: {width: 1920, height: 1080}});
  for (const [src, out] of jobs) {
    await p.goto('file://' + src);
    await p.waitForLoadState('networkidle');
    await p.evaluate(async () => { await document.fonts.ready; window.fit(); });
    await p.screenshot({path: out});
  }
  await b.close();
})();
