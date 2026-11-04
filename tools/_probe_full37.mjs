import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p = await browser.newPage();
  await p.setUserAgent(UAS);
  await p.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p.goto("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await p.type("#identifierId", "xbot0x9f9i3@gmail.com", { delay: 20 });
  await p.evaluate(() => document.querySelector("#identifierNext").click());
  for (let i = 0; i < 12; i++) {
    await sleep(1000);
    const st = await p.evaluate(() => ({
      url: location.href.slice(0, 80),
      pw: !!document.querySelector("[name='passwd']"),
      rej: /Impossible de vous connecter|trouver ce compte|not be secure/i.test(document.body.innerText),
      txt: document.body.innerText.replace(/\n+/g, " | ").slice(0, 220),
    }));
    console.log(i, JSON.stringify(st));
    if (st.pw) break;
  }
} finally { await browser.close(); }
