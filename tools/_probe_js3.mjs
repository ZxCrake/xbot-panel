import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p = await browser.newPage();
  await p.setUserAgent(UAS);
  await p.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p.goto("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await sleep(1000);
  const html = await p.content();
  const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
  const usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
  let bg = g(/name="bgresponse"[^>]*value="([^"]*)"/, html);
  console.log("inputs bgresponse:", JSON.stringify(bg));
  if (!bg || bg.length < 50) {
    const d = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", method: "userrecaptcha", googlekey: "6Lf-_ekqAAAAAO4AXrJISaHw4_bW76NcfwhLN7Is", pageurl: "https://accounts.google.com/v3/signin/identifier", enterprise: "1" }) })).json();
    bg = "";
    for (let i = 0; i < 30 && !bg; i++) { await sleep(2500); const r2 = await (await fetch(`https://2captcha.com/res.php?key=${KEY}&action=get&id=${d.request}&json=1`)).json(); if (r2 && r2.status === 1 && r2.request && r2.request !== "NOT_FOUND") bg = String(r2.request); }
  }
  console.log("bg len:", bg.length);
  const ck = (await browser.cookies()).map((c) => `${c.name}=${c.value}`).join("; ");
  const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
  const p1 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: ck }, body: new URLSearchParams({ identifier: "xbot0uvl1d70@gmail.com", hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: bg, action: "1", at }) });
  const h1 = await p1.text();
  console.log("S1:", p1.status, "url:", decodeURIComponent(p1.url).slice(0, 160));
  console.log("passwd:", /name="passwd"/.test(h1), "| txt:", h1.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 220));
} finally { await browser.close(); }
