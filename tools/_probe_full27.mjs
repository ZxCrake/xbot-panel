import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p2 = await browser.newPage();
  await p2.setUserAgent(UAS);
  await p2.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p2.goto("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await sleep(1500);
  const vals = await p2.evaluate(() => { const o = {}; for (const i of document.querySelectorAll("input")) { const n = i.getAttribute("name"); if (n) o[n] = i.value; } return o; });
  const ck = await browser.cookies();
  const jarS = ck.map((c) => `${c.name}=${c.value}`).join("; ");
  console.log("bg len:", (vals.bgresponse || "").length, "checkConn:", vals.checkConnection);
  const act = `https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&dsh=${encodeURIComponent(vals.usi)}&emr=1&flowEntry=ServiceLogin&flowName=WebLiteSignIn&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail`;
  const p1 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jarS }, body: new URLSearchParams({ identifier: "xbot0w4mxj6@gmail.com", hiddenPassword: "", usi: vals.usi, domain: "", region: vals.region, bgresponse: vals.bgresponse, pstMsg: vals.pstMsg, checkConnection: vals.checkConnection, checkedDomains: vals.checkedDomains, action: "1", at: vals.at }) });
  const h1 = await p1.text();
  console.log("full url:", decodeURIComponent(p1.url));
  console.log("txt:", h1.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 260));
} finally { await browser.close(); }
