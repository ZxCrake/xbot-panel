import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p2 = await browser.newPage();
  await p2.setUserAgent(UAS);
  await p2.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p2.goto("https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await sleep(1200);
  const vals = await p2.evaluate(() => { const o = {}; for (const i of document.querySelectorAll("input")) { const n = i.getAttribute("name") || i.id || i.getAttribute("jsname"); o[n] = i.value || ""; } return o; });
  console.log("nojs vals:", JSON.stringify(Object.fromEntries(Object.entries(vals).map(([k, v]) => [k, String(v).slice(0, 18)]))));
  const ck = await browser.cookies();
  const jarS = ck.map((c) => `${c.name}=${c.value}`).join("; ");
  const url = "https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
  const body = new URLSearchParams({ PageNum: "1", identifier: "xbot0x4y8047@gmail.com", hiddenPassword: "", usi: vals.usi, domain: "", region: vals.region, ct: vals.ct, ca: "", action: "1" });
  const p = await fetch(url, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jarS }, body });
  const h = await p.text();
  console.log("POST:", p.status, decodeURIComponent(p.url).slice(0, 140));
  console.log("txt:", h.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 300));
} finally { await browser.close(); }
