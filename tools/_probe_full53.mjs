import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
function toks(html) {
  return {
    usi: g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html),
    at: g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html),
    bg: g(/name="bgresponse"[^>]*value="([^"]*)"/, html),
    region: g(/name="region"[^>]*value="([^"]*)"/, html) || "FR",
  };
}
async function inPost(params) {
  const d = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", ...params }) })).json();
  return String(d.request);
}
async function waitRes(id) {
  for (let i = 0; i < 30; i++) { await sleep(2500);
    const d = await (await fetch(`https://2captcha.com/res.php?key=${KEY}&action=get&id=${id}&json=1`)).json();
    if (d && d.status === 1 && d.request && d.request !== "NOT_FOUND") return String(d.request); }
  return "";
}
const SITEKEY = "6Lf-_ekqAAAAAO4AXrJISaHw4_bW76NcfwhLN7Is";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
async function readCode(browser, email, password, label) {
  const p = await browser.newPage();
  try {
    await p.setUserAgent(UAS);
    await p.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
    const GETU = "https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
    await p.goto(GETU, { waitUntil: "networkidle2" });
    await sleep(1500);
    const html1 = await p.content();
    const t1 = toks(html1);
    const bg = t1.bg && t1.bg.length > 50 ? t1.bg : (await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: GETU, enterprise: "1" })));
    const ck = (await browser.cookies()).map((c) => `${c.name}=${c.value}`).join("; ");
    const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(t1.usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
    const H = { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded" };
    const p1 = await fetch(act, { method: "POST", headers: { ...H, cookie: ck }, body: new URLSearchParams({ identifier: email, hiddenPassword: "", usi: t1.usi, domain: "", region: t1.region, bgresponse: bg, action: "1", at: t1.at }) });
    const h1 = await p1.text();
    const url1 = decodeURIComponent(p1.url);
    console.log(label, "S1:", p1.status, "rrk:", (url1.match(/rrk=(\d+)/) || [])[1] || "-", "passwd:", /name="passwd"/.test(h1));
    if (!/name="passwd"/.test(h1)) return "";
    const t2 = toks(h1);
    const p2 = await fetch(act, { method: "POST", headers: { ...H, cookie: ck }, body: new URLSearchParams({ PageNum: "2", passwd: password, at: t2.at, usi: t2.usi || t1.usi, domain: "", region: t2.region, bgresponse: "js_disabled", action: "2" }) });
    const h2 = await p2.text();
    const body = h2.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
    return (body.match(/\b(\d{6})\b/) || [])[1] || "";
  } finally { await p.close(); }
}
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

  let code = "";
  const t0 = Date.now();
  for (let i = 0; i < 40 && !code; i++) {
    code = await readCode(browser, email, password, "try" + (i + 1));
    if (!code) await sleep(4000);
  }
  console.log("elapsed:", ((Date.now() - t0) / 1000).toFixed(0) + "s", "CODE:", code || "(none)");
  if (code) {
    await (await page.$("[name='code']")).type(code, { delay: 25 });
    await next(); await sleep(2500);
    console.log("FINAL:", (await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 200))));
  }
} finally { await browser.close(); }
