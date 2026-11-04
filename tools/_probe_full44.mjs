import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const page = await browser.newPage();
  await page.setUserAgent(UAS);
  await page.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await page.goto("https://accounts.google.com/signup", { waitUntil: "networkidle2" });
  const stamp = Date.now().toString(36).slice(-6);
  const email = `xbot${stamp}${Math.floor(Math.random() * 90)}@gmail.com`;
  const password = `Xb-${stamp}-${Math.floor(Math.random() * 9000 + 1000)}`;
  console.log("email:", email, "pass:", password);
  const next = async () => page.evaluate(() => { const b = [...document.querySelectorAll("button")].find((x) => /^(suivant|next)$/i.test((x.textContent || "").trim())); if (b) b.click(); });
  await page.waitForSelector("#firstName");
  await page.type("#firstName", "Xbot"); await page.type("#lastName", stamp); await next(); await sleep(1800);
  await page.type("#day", "15"); await page.type("#year", "1990");
  await page.evaluate(() => { const m = [...document.querySelectorAll("input")].find((i) => !i.id && i.getAttribute("jsname") === "YPqjbf"); if (m) { m.click(); m.focus(); } });
  await sleep(600);
  await page.evaluate(() => { const o = [...document.querySelectorAll("li[role=option],li")].find((l) => /^janvier$/i.test((l.textContent || "").trim())); if (o) o.click(); });
  await sleep(300);
  await page.evaluate(() => { const el = [...document.querySelectorAll("li,[role=option]")].find((x) => /^(homme|male)$/i.test((x.textContent || "").trim())); if (el) el.click(); });
  await sleep(300); await next(); await sleep(1800);
  if (!(await page.$("#emailPhone"))) await next(); await sleep(1800);
  await page.type("#emailPhone", email); await next(); await sleep(2400);
  const src = await page.evaluate(() => { const f = [...document.querySelectorAll("iframe")].map((x) => x.getAttribute("src")).find((s) => s && s.includes("recaptcha")); return f || ""; });
  if (src) {
    const d = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", method: "userrecaptcha", googlekey: (src.match(/[?&]k=([-\w]+)/) || [])[1], pageurl: page.url(), enterprise: "1" }) })).json();
    let token = "";
    for (let i = 0; i < 40 && !token; i++) { await sleep(2500); const r2 = await (await fetch(`https://2captcha.com/res.php?key=${KEY}&action=get&id=${d.request}&json=1`)).json(); if (r2 && r2.status === 1 && r2.request && r2.request !== "NOT_FOUND") token = r2.request; }
    await page.evaluate((t) => { for (const ta of document.querySelectorAll("#g-recaptcha-response,[name='g-recaptcha-response']")) ta.value = t; const i2 = document.querySelector("iframe")?.contentDocument?.getElementById("g-recaptcha-response"); if (i2) i2.value = t; }, token);
    await next(); await sleep(2400);
  }
  const html = await page.evaluate(() => document.documentElement.outerHTML);
  const codes = [...new Set((html.match(/\b\d{6}\b/g) || []))];
  console.log("n:", codes.length);
  const ck = await browser.cookies();
  const jarS = ck.map((c) => `${c.name}=${c.value}`).join("; ");
  const at = g(html, /name="at"[^>]*value="([^"]+)"/) || g(html, /"SNlM0e":"([^"]+)"/);
  const usi = g(html, /name="usi"[^>]*value="([^"]+)"/) || g(html, /"Qzxixc":"([^"]+)"/);
  function g(h, re) { return (re.exec(h) || [])[1] || ""; }
  console.log("at:", at.slice(0, 14), "usi:", usi.slice(0, 14));
  for (let pass = 1; pass <= 2; pass++) {
    let r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: { "User-Agent": UAS, cookie: jarS } });
    let h = await r.text();
    const a2 = g(h, /name="at"[^>]*value="([^"]+)"/) || g(h, /"SNlM0e":"([^"]+)"/);
    const u2 = g(h, /name="usi"[^>]*value="([^"]+)"/) || g(h, /"Qzxixc":"([^"]+)"/);
    const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(u2)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
    const p1 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jarS }, body: new URLSearchParams({ identifier: email, hiddenPassword: "", usi: u2, domain: "", region: "FR", bgresponse: "", action: "1", at: a2 }) });
    let h1 = await p1.text();
    const url1 = decodeURIComponent(p1.url);
    console.log("pass", pass, "id1:", p1.status, "rrk:", (url1.match(/rrk=(\d+)/) || [])[1], "idnf:", /idnf=/.test(url1), "passwd:", /name="passwd"/.test(h1));
    if (/name="passwd"/.test(h1)) { console.log("  -> ACCOUNT ACTIVE, suite non impl."); break; }
    await sleep(5000);
  }
} finally { await browser.close(); }
