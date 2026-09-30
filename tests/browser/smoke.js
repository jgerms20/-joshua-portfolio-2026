// Browser smoke test: loads every public page at phone and desktop sizes and
// exercises the interactive bits. Run by .github/workflows/weekly-update.yml.
//
//   npm install --no-save playwright && npx playwright install chromium
//   python3 -m http.server 8765 &   # from the repo root
//   node tests/browser/smoke.js
//
// Fails (exit 1) on page errors, broken local requests, sideways scrolling,
// or a broken interaction. External hosts (YouTube, Spotify, fonts) are
// ignored: they can be down without the site being broken.
const { chromium } = require('playwright');

const BASE = process.env.SMOKE_BASE || 'http://localhost:8765/';
const PAGES = [
  'index.html', 'photography/', 'shop.html',
  'podcasts/podcast-eclectic-polymath.html', 'podcasts/podcast-dominate.html',
  'podcasts/podcast-approachable-ai.html', 'podcasts/podcast-curious-creative.html',
  'work/work-gatorade.html', 'work/work-levis.html', 'work/work-sephora.html',
  'work/work-xfinity.html', 'work/work-directv.html', 'work/work-doordash.html',
];
const SIZES = [[390, 844], [1440, 900]];

const failures = [];
const fail = (where, what) => failures.push(`${where}: ${what}`);

async function checkPage(browser, path, [w, h]) {
  const where = `${path} @${w}`;
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  page.on('pageerror', e => fail(where, `page error: ${e.message}`));
  page.on('response', r => {
    // data/episodes/*.json is optional: it only exists once a show's feed is configured
    if (r.url().startsWith(BASE) && r.status() >= 400 && !r.url().includes('/data/episodes/')) fail(where, `${r.status()} ${r.url()}`);
  });
  await page.goto(BASE + path, { waitUntil: 'load', timeout: 45000 });
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 800) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(600);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  if (overflow > 1) fail(where, `sideways scroll of ${overflow}px`);
  const broken = await page.evaluate(() => [...document.images]
    .filter(i => i.complete && i.naturalWidth === 0 && i.currentSrc.startsWith(location.origin))
    .map(i => i.currentSrc));
  broken.forEach(src => fail(where, `broken image ${src}`));
  return page;
}

async function interactions(browser) {
  // Homepage gallery: See more, filters, lightbox
  let page = await checkPage(browser, 'index.html', [1440, 900]);
  const visible = () => page.evaluate(() => [...document.querySelectorAll('#photoGallery .photo-item')].filter(t => t.offsetParent).length);
  const before = await visible();
  await page.click('#photography .gallery-more');
  if ((await visible()) <= before) fail('index gallery', 'See more did not reveal more photos');
  await page.click('#photography .photo-chapter[data-filter="people"]');
  const cats = await page.evaluate(() => [...document.querySelectorAll('#photoGallery .photo-item')].filter(t => t.offsetParent).map(t => t.dataset.cat));
  if (!cats.length || cats.some(c => c !== 'people')) fail('index gallery', 'People filter shows other photos');
  await page.click('#photoGallery .photo-item:not(.hide)');
  if (!(await page.evaluate(() => document.getElementById('lightbox').classList.contains('open')))) fail('index gallery', 'lightbox did not open');
  await page.keyboard.press('Escape');
  for (const id of ['about', 'podcasts', 'photography', 'ai', 'work', 'projects', 'media-diet', 'contact']) {
    if (!(await page.$(`#${id}`))) fail('index nav', `missing section #${id}`);
  }
  await page.close();

  // Photography site: a set opens in the viewer; booking form builds a mailto
  page = await checkPage(browser, 'photography/', [390, 844]);
  const setLink = await page.$('[data-set], a[href^="#"][class*="set"]');
  if (setLink) {
    await setLink.click();
    await page.waitForTimeout(300);
    const open = await page.evaluate(() => !!document.querySelector('dialog[open], .is-open[role="dialog"], [aria-modal="true"]:not([hidden])'));
    if (!open) fail('photography', 'photo set did not open');
    await page.keyboard.press('Escape');
  }
  await page.close();

  // Shop: open a print, add to cart, cart count updates
  page = await checkPage(browser, 'shop.html', [1440, 900]);
  await page.click('.shop-card');
  await page.click('#addToCartBtn');
  const count = await page.textContent('#cartCount');
  if (count.trim() !== '1') fail('shop', `cart count is "${count}" after adding one print`);
  await page.close();
}

(async () => {
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  for (const path of PAGES) {
    for (const size of SIZES) {
      try { await (await checkPage(browser, path, size)).close(); }
      catch (e) { fail(`${path} @${size[0]}`, e.message.split('\n')[0]); }
    }
  }
  try { await interactions(browser); } catch (e) { fail('interactions', e.message.split('\n')[0]); }
  await browser.close();
  if (failures.length) {
    console.error(`Smoke test found ${failures.length} problem(s):\n- ` + failures.join('\n- '));
    process.exit(1);
  }
  console.log(`Smoke test passed: ${PAGES.length} pages x ${SIZES.length} sizes, plus gallery, photo site and shop interactions.`);
})();
