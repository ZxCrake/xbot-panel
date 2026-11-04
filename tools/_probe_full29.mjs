import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p2 = await browser.newPage();
  await p2.setUserAgent(UAS);
  await p2.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p2.goto("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  for (let i = 0; i < 10; i++) {
    await sleep(800);
    const all = await p2.evaluate(() => [...document.querySelectorAll("input")].map((x) => `${x.getAttribute("name") || x.getAttribute("jsname") || x.id || "?"}=[${(x.value || "").length}]=${(x.value || "").slice(0, 16)}`));
    console.log(i, JSON.stringify(all));
  }
  console.log("iframes:", await p2.evaluate(() => [...document.querySelectorAll("iframe")].map((f) => (f.getAttribute("src") || "").slice(0, 90))));
} finally { await browser.close(); }
