import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p2 = await browser.newPage();
  await p2.setUserAgent(UA);
  await p2.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p2.goto("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await p2.type("#identifierId", "xbot0uwbzb67@gmail.com", { delay: 25 });
  await p2.evaluate(() => document.querySelector("#identifierNext").click());
  await sleep(3000);
  console.log("U:", p2.url().slice(0, 130));
  console.log("T:", await p2.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 300)));
  console.log("passwd:", !!(await p2.$("[name='passwd']")));
} finally { await browser.close(); }
