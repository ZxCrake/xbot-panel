import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p = await browser.newPage();
  await p.setUserAgent(UAS);
  await p.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  p.on("response", async (rs) => {
    try {
      const u = rs.url();
      if (u.includes("batchexecute") || u.includes("browserinfo")) {
        console.log("URL:", decodeURIComponent(u).slice(0, 220));
        console.log("  POST:", rs.request().postData());
        console.log("  RESP:", (await rs.text()).slice(0, 500).replace(/\n/g, " "));
        console.log("--");
      }
    } catch {}
  });
  await p.goto("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await sleep(1500);
  await p.type("#identifierId", "xbot0y2u8155@gmail.com", { delay: 20 });
  await p.evaluate(() => document.querySelector("#identifierNext").click());
  await sleep(3500);
  console.log("FINAL txt:", await p.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 220)));
} finally { await browser.close(); }
