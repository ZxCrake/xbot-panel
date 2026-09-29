// Run with Node and Playwright. All responses are local fixtures; no X calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const attack = '<img src=x onerror="window.__xss=1"><svg onload="window.__xss=1"></svg>';
const article = '<p onclick="window.__xss=1">Hello <b>world</b></p>' + attack +
  '<a href="javascript:window.__xss=1">bad</a><a href="https://example.com/">good</a>';
const csp = "default-src 'self'; script-src 'self'; object-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:";

(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.BROWSER_EXECUTABLE ? { executablePath: process.env.BROWSER_EXECUTABLE } : {}) });
  try {
    const context = await browser.newContext();
    const errors = [];
    const unexpected = [];
    await context.addInitScript(() => {
      localStorage.setItem('token', 'synthetic-token');
      localStorage.setItem('username', 'boss');
      localStorage.setItem('is_admin', '1');
    });
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.origin !== 'http://xbot.test') return route.abort();
      const pathname = url.pathname;
      let data;
      if (pathname === '/api/admin/users') data = { users: [{ username: 'member', accounts: 1, running: false }] };
      else if (pathname === '/api/admin/users/member/detail') data = {
        live: {}, config: {}, files: {}, history: [{ t: 1, action: attack, msg: attack, ok: false }]
      };
      else if (pathname === '/api/status') data = { running: false, log: [{ msg: attack, ok: false }] };
      else if (pathname === '/api/actions') data = { 3: 'Like' };
      else if (pathname === '/api/config') data = { threads: 5, pfp_image: 'pfp.jpg' };
      else if (pathname === '/api/articles') data = { articles: [{ title: attack, body: article }] };
      else if (pathname.startsWith('/api/file/')) data = { content: '' };
      else if (pathname.startsWith('/api/')) {
        unexpected.push(pathname);
        return route.abort();
      }
      if (data) return route.fulfill({ json: data });
      const pages = { '/': 'index.html', '/admin': 'admin.html', '/login': 'login.html', '/admin/login': 'admin_login.html' };
      const file = pages[pathname]
        ? path.join(root, 'xbot/templates', pages[pathname])
        : path.join(root, 'xbot', pathname);
      if (!fs.existsSync(file)) return route.fulfill({ status: 404, body: '' });
      const type = file.endsWith('.js') ? 'application/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html';
      return route.fulfill({ contentType: type, body: fs.readFileSync(file), headers: { 'Content-Security-Policy': csp } });
    });
    const page = await context.newPage();
    page.on('pageerror', err => errors.push(err.message));
    await page.goto('http://xbot.test/admin');
    await page.waitForFunction(() => document.querySelector('#usersBody').textContent.includes('member'));
    await page.evaluate(() => selectUser('member'));
    assert((await page.locator('#histView').textContent()).includes(attack));
    assert.equal(await page.locator('#histView img, #histView svg').count(), 0);
    assert.equal(await page.evaluate(() => window.__xss), undefined);
    await page.goto('http://xbot.test/');
    await page.waitForFunction(() => document.querySelector('#artList').textContent.includes('img'));
    await page.evaluate(() => selectArt(0));
    assert.equal(await page.locator('#artBody img, #artBody svg, #artBody [onclick]').count(), 0);
    assert.equal(await page.locator('#artBody b').textContent(), 'world');
    assert.deepEqual(await page.locator('#artBody a').evaluateAll(links => links.map(a => a.getAttribute('href'))),
      [null, 'https://example.com/']);
    assert((await page.locator('#log').textContent()).includes(attack));
    assert.equal(await page.locator('#log img, #log svg').count(), 0);
    assert.equal(await page.evaluate(() => window.__xss), undefined);
    assert.deepEqual(errors, []);
    assert.deepEqual(unexpected, []);
    console.log('Browser security checks passed: admin history, user logs, rich-text sanitization, external scripts.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
