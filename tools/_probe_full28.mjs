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

  // page GlifWebSignIn (v2) rendue par JS : bgresponse long token
  const p2 = await browser.newPage();
  await p2.setUserAgent(UAS);
  await p2.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p2.goto("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  let vals = {};
  for (let i = 0; i < 15; i++) {
    await sleep(800);
    vals = await p2.evaluate(() => { const o = {}; for (const i of document.querySelectorAll("input")) { const n = i.getAttribute("name"); if (n) o[n] = i.value; } return o; });
    if ((vals.bgresponse || "").length > 50) break;
  }
  console.log("bg len:", (vals.bgresponse || "").length, "at:", (vals.at || "").slice(0, 14), "usi:", (vals.usi || "").slice(0, 16));
  const ck = await browser.cookies();
  const jarS = ck.map((c) => `${c.name}=${c.value}`).join("; ");
  const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(vals.usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
  const p1 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jarS }, body: new URLSearchParams({ identifier: email, hiddenPassword: "", usi: vals.usi, domain: "", region: vals.region || "FR", bgresponse: vals.bgresponse, action: "1", at: vals.at }) });
  let h1 = await p1.text();
  console.log("id1:", p1.status, decodeURIComponent(p1.url).slice(0, 120), "passwd:", /name="passwd"/.test(h1));
  if (/name="passwd"/.test(h1)) {
    const at2 = g(/name="at"[^>]*value="([^"]+)"/, h1);
    const usi2 = g(/name="usi"[^>]*value="([^"]+)"/, h1) || vals.usi;
    const bg2 = g(/name="bgresponse"[^>]*value="([^"]*)"/, h1) || vals.bgresponse;
    const p3 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jarS }, body: new URLSearchParams({ PageNum: "2", passwd: password, at: at2, usi: usi2, bgresponse: bg2, action: "2", domain: "", region: "FR" }) });
    let h3 = await p3.text();
    console.log("id2:", p3.status, decodeURIComponent(p3.url).slice(0, 120));
    const body = h3.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
    let code = (body.match(/\b(\d{6})\b/) || [])[1] || "";
    console.log("CODE:", code || "(none)");
    if (code) {
      await (await page.$("[name='code']")).type(code, { delay: 25 });
      await next(); await sleep(2600);
      console.log("FINAL:", (await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 180))));
    }
  }
} finally { await browser.close(); }
