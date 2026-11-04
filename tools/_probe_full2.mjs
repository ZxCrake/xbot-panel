import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"] });
try {
  const page = await browser.newPage();
  await page.goto("https://accounts.google.com/signup", { waitUntil: "networkidle2" });
  const stamp = Date.now().toString(36).slice(-6);
  const email = `xbot${stamp}${Math.floor(Math.random() * 90)}@gmail.com`;
  console.log("email:", email);
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
  await page.type("#emailPhone", email); await next(); await sleep(2500);
  const src = await page.evaluate(() => { const f = [...document.querySelectorAll("iframe")].map((x) => x.getAttribute("src")).find((s) => s && s.includes("recaptcha")); return f || ""; });
  if (src) {
    const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
    const id = await (await (await fetch("https://2captcha.com/in.php", { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", method: "userrecaptcha", googlekey: (src.match(/[?&]k=([-\w]+)/) || [])[1], pageurl: page.url(), enterprise: "1" }) })).json()).request;
    let token = "";
    for (let i = 0; i < 40 && !token; i++) { await sleep(2500); const d = await (await fetch(`https://2captcha.com/res.php?key=${KEY}&action=get&id=${id}&json=1`)).json(); if (d && d.status === 1 && d.request && d.request !== "NOT_FOUND") token = d.request; }
    await page.evaluate((t) => { for (const ta of document.querySelectorAll("#g-recaptcha-response,[name='g-recaptcha-response']")) ta.value = t; const i2 = document.querySelector("iframe")?.contentDocument?.getElementById("g-recaptcha-response"); if (i2) i2.value = t; }, token);
    await next(); await sleep(2500);
  }
  console.log("P1:", await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 160)));

  // —— onglet 2 : lecture de la boîte dans la même session ——
  const p2 = await browser.newPage();
  await p2.goto("https://mail.google.com/mail/u/0/", { waitUntil: "networkidle2" });
  await sleep(2500);
  const t2 = await p2.evaluate(() => ({ url: location.href, txt: document.body.innerText.replace(/\n+/g, " | ").slice(0, 500) }));
  console.log("P2:", JSON.stringify(t2));
  const m = t2.txt.match(/\b\d{6}\b/);
  console.log("code:", m ? m[1] : "(none)");
} finally { await browser.close(); }
