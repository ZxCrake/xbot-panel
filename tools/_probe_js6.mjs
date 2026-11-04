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
  await p.type("#identifierId", "xbot0uvl1d70@gmail.com", { delay: 20 });
  await p.evaluate(() => document.querySelector("#identifierNext").click());
  await sleep(2500);
  const html = await p.content();
  const usi = g(/name="usi"[^>]*value="([^"]+)"/, html);
  const ct = g(/name="ct"[^>]*value="([^"]+)"/, html);
  const region = g(/name="region"[^>]*value="([^"]+)"/, html) || "FR";
  const ca0 = g(/name="ca"[^>]*value="([^"]*)"/, html);
  console.log("usi:", usi.slice(0, 18), "| ct:", JSON.stringify(ct.slice(0, 30)), "| ca:", JSON.stringify(ca0.slice(0, 30)), "| len", html.length);
  const ck = (await browser.cookies()).map((c) => `${c.name}=${c.value}`).join("; ");
  // 1) POST avec ct (si présent) sinon SNlM0e
  const at = ct || g(/"SNlM0e":"([^"]+)"/, html);
  const p1 = await fetch(`https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin`, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: ck }, body: new URLSearchParams({ PageNum: "1", identifier: "xbot0uvl1d70@gmail.com", hiddenPassword: "", usi, domain: "", region, ct: at, ca: "" }) });
  const h1 = await p1.text();
  console.log("POST v3:", p1.status, "| passwd:", /name="passwd"/.test(h1), "| txt:", h1.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 220));
} finally { await browser.close(); }
