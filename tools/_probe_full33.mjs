import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p2 = await browser.newPage();
  await p2.setUserAgent(UAS);
  await p2.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  p2.on("request", (rq) => { if (rq.method() === "POST") console.log("POST", rq.url().slice(0, 120), "::", (rq.postData() || "").slice(0, 700)); });
  await p2.goto("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await sleep(1000);
  await p2.type("#identifierId", "xbot0uvl1d70@gmail.com", { delay: 20 });
  await p2.evaluate(() => document.querySelector("#identifierNext").click());
  await sleep(3500);
  const hasPw = await p2.$("[name='passwd']");
  console.log("PASSWD:", !!hasPw, "| txt:", await p2.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 200)));
  if (hasPw) {
    await hasPw.type("Xb-0uvl1d-6329", { delay: 20 });
    await p2.evaluate(() => document.querySelector("#passwordNext")?.click());
    await sleep(4000);
    const t = await p2.evaluate(() => (document.querySelector("div[role=main]") || document.body).innerText);
    console.log("U2:", p2.url().slice(0, 110));
    console.log("T2:", t.replace(/\n+/g, " | ").slice(0, 300));
  }
} finally { await browser.close(); }
