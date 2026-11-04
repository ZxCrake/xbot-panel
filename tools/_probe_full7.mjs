import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const page = await browser.newPage();
  await page.setUserAgent(UA);
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
  console.log("P1:", (await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 120))));

  // —— tab 2 : WebLite dans le MÊME navigateur (cookies partagés) ——
  const p2 = await browser.newPage();
  await p2.setUserAgent(UA);
  await p2.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p2.goto("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await p2.type("#identifierId", email, { delay: 25 });
  await p2.evaluate(() => document.querySelector("#identifierNext").click());
  let state = "";
  for (let i = 0; i < 30 && !state; i++) {
    await sleep(500);
    state = await p2.evaluate(() => {
      const t = document.body.innerText;
      if (document.querySelector("[name='passwd']")) return "PASSWD";
      if (/trouver ce compte|not be found/i.test(t)) return "NOTFOUND";
      return "";
    });
  }
  console.log("T2:", state, p2.url().slice(0, 120));
  if (state === "PASSWD") {
    await (await p2.$("[name='passwd']")).type(password, { delay: 25 });
    await p2.evaluate(() => document.querySelector("#passwordNext")?.click());
    let code = "";
    for (let i = 0; i < 40 && !code; i++) {
      await sleep(600);
      code = await p2.evaluate(() => { const t = (document.querySelector("div[role=main]") || document.body).innerText; return (t.match(/\b\d{6}\b/) || [])[1] || ""; });
    }
    console.log("CODE:", code || "(none)");
    if (code) {
      await (await page.$("[name='code']")).type(code, { delay: 25 });
      await next(); await sleep(2500);
      console.log("FINAL:", (await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 200))));
    }
  }
} finally { await browser.close(); }
