import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p = await browser.newPage();
  await p.setUserAgent(UAS);
  await p.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p.goto("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await sleep(800);
  await p.type("#identifierId", "xbot0uvl1d70@gmail.com", { delay: 20 });
  await p.evaluate(() => document.querySelector("#identifierNext").click());
  for (let i = 0; i < 16; i++) {
    await sleep(1000);
    const st = await p.evaluate(() => {
      const t = document.body.innerText;
      return {
        rej: /Couldn|Impossible|secure/i.test(t),
        pw: !!document.querySelector("[name='passwd']"),
        txt: t.replace(/\n+/g, " | ").slice(0, 180),
        url: location.href.slice(0, 120),
      };
    });
    console.log(i, JSON.stringify(st));
    if (st.pw || st.rej) break;
  }
} finally { await browser.close(); }
