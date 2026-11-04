import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p2 = await browser.newPage();
  await p2.setUserAgent(UAS);
  await p2.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p2.goto("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await sleep(1200);
  await p2.type("#identifierId", "xbot0w4mxj6@gmail.com", { delay: 20 });
  await p2.evaluate(() => document.querySelector("#identifierNext").click());
  await sleep(2500);
  console.log("T:", await p2.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 160)));
  // 2e tentative après délai (provisioning asynchrone)
  await sleep(5000);
  await p2.evaluate(() => document.querySelector("#identifierNext")?.click());
  await sleep(3000);
  console.log("T2:", await p2.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 160)));
  console.log("inputs:", await p2.evaluate(() => [...document.querySelectorAll("input")].map((i) => `${i.getAttribute("name") || i.id}=${(i.value || "").slice(0, 12)}`).join(" ; ")));
} finally { await browser.close(); }
