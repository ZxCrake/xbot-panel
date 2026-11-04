import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
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
  await page.type("#firstName", "Xbot"); await page.type("#lastName", stamp); await next(); await sleep(1600);
  await page.type("#day", "15"); await page.type("#year", "1990");
  await page.evaluate(() => { const m = [...document.querySelectorAll("input")].find((i) => !i.id && i.getAttribute("jsname") === "YPqjbf"); if (m) { m.click(); m.focus(); } });
  await sleep(600);
  await page.evaluate(() => { const o = [...document.querySelectorAll("li[role=option],li")].find((l) => /^janvier$/i.test((l.textContent || "").trim())); if (o) o.click(); });
  await sleep(300);
  await page.evaluate(() => { const el = [...document.querySelectorAll("li,[role=option]")].find((x) => /^(homme|male)$/i.test((x.textContent || "").trim())); if (el) el.click(); });
  await sleep(300); await next(); await sleep(1600);
  if (!(await page.$("#emailPhone"))) await next(); await sleep(1600);
  await page.type("#emailPhone", email); await next(); await sleep(2200);
  const src = await page.evaluate(() => { const f = [...document.querySelectorAll("iframe")].map((x) => x.getAttribute("src")).find((s) => s && s.includes("recaptcha")); return f || ""; });
  if (src) {
    const d = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", method: "userrecaptcha", googlekey: (src.match(/[?&]k=([-\w]+)/) || [])[1], pageurl: page.url(), enterprise: "1" }) })).json();
    let token = "";
    for (let i = 0; i < 40 && !token; i++) { await sleep(2500); const r2 = await (await fetch(`https://2captcha.com/res.php?key=${KEY}&action=get&id=${d.request}&json=1`)).json(); if (r2 && r2.status === 1 && r2.request && r2.request !== "NOT_FOUND") token = r2.request; }
    await page.evaluate((t) => { for (const ta of document.querySelectorAll("#g-recaptcha-response,[name='g-recaptcha-response']")) ta.value = t; const i2 = document.querySelector("iframe")?.contentDocument?.getElementById("g-recaptcha-response"); if (i2) i2.value = t; }, token);
    await next(); await sleep(2200);
  }
  const ck = await browser.cookies();
  const jarS = ck.map((c) => `${c.name}=${c.value}`).join("; ");

  async function tryNojs() {
    const r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: { "User-Agent": UAS } });
    let html = await r.text();
    const usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
    const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
    const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
    const p1 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jarS }, body: new URLSearchParams({ identifier: email, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: "", action: "1", at }) });
    const h1 = await p1.text();
    if (!/name="passwd"/.test(h1)) return { st: "idnf", h1 };
    const at2 = g(/name="at"[^>]*value="([^"]+)"/, h1) || g(/"SNlM0e":"([^"]+)"/, h1);
    const p2 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jarS }, body: new URLSearchParams({ passwd: password, at: at2, action: "2" }) });
    const h2 = await p2.text();
    const body = h2.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
    const m = body.match(/\b(\d{6})\b/);
    return { st: m ? "CODE" : "no-code", code: m && m[1] };
  }
  let out = null;
  for (let i = 0; i < 24; i++) {
    out = await tryNojs();
    console.log(`try ${i + 1}:`, out.st, out.code || "");
    if (out.st === "CODE") break;
    await sleep(4000);
  }
  if (out && out.code) {
    await (await page.$("[name='code']")).type(out.code, { delay: 25 });
    await next(); await sleep(2500);
    console.log("FINAL:", (await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 200))));
  }
} finally { await browser.close(); }
