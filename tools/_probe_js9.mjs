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
      if (u.includes("batchexecute")) console.log("RPC", (u.match(/rpcids=([\w-]+)/) || [])[1], "::", (await rs.text()).slice(0, 400).replace(/\n/g, " "));
    } catch {}
  });
  await p.goto("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await sleep(1200);
  console.log("inputs:", await p.evaluate(() => [...document.querySelectorAll("input")].map((i) => `${i.getAttribute("name") || i.id}=${(i.value || "").slice(0, 16)}`).join(" ; ")));
  await p.type("#identifierId", "xbot0uvl1d70@gmail.com", { delay: 20 });
  await p.evaluate(() => document.querySelector("#identifierNext").click());
  await sleep(3500);
  console.log("after-id:", await p.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 220)));
} finally { await browser.close(); }
