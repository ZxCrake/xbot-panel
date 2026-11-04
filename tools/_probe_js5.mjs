import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p = await browser.newPage();
  await p.setUserAgent(UAS);
  await p.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p.goto("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await p.type("#identifierId", "xbot0uvl1d70@gmail.com", { delay: 20 });
  await p.evaluate(() => document.querySelector("#identifierNext").click());
  for (let i = 0; i < 15; i++) {
    await sleep(1000);
    const st = await p.evaluate(() => ({
      pw: !!document.querySelector("[name='passwd']"),
      has: [...document.querySelectorAll("input")].map((x) => x.getAttribute("name") || x.id || x.getAttribute("jsname")).join(","),
    }));
    if (st.pw) { console.log(i, "PASSWD arrive"); break; }
    if (i % 5 === 4) console.log(i, st.has.slice(0, 160));
  }
  const pw = await p.$("[name='passwd']");
  if (pw) {
    await pw.type("Xb-0uvl1d-6329", { delay: 20 });
    await p.evaluate(() => document.querySelector("#passwordNext")?.click());
    await sleep(4000);
    console.log("URL2:", p.url().slice(0, 130));
    console.log("T2:", await p.evaluate(() => (document.querySelector("div[role=main]") || document.body).innerText.replace(/\n+/g, " | ").slice(0, 400)));
  } else {
    console.log("FINAL:", await p.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 220)));
  }
} finally { await browser.close(); }
