import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({
  headless: "new",
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"],
});
try {
  const page = await browser.newPage();
  await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36");
  await page.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
  });
  await page.goto("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  console.log("webdriver:", await page.evaluate(() => String(navigator.webdriver)));
  await page.type("#identifierId", "xbot0vjei070@gmail.com", { delay: 25 });
  await page.evaluate(() => document.querySelector("#identifierNext").click());
  let hasPw = false;
  for (let i = 0; i < 20 && !hasPw; i++) { await sleep(500); hasPw = !!(await page.$("[name='passwd']")); }
  console.log("U1:", page.url().slice(0, 130));
  console.log("T1:", await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 260)));
  if (hasPw) {
    await (await page.$("[name='passwd']")).type("Xb-0vjei0-9641", { delay: 25 });
    await page.evaluate(() => document.querySelector("#passwordNext")?.click());
    let code = "";
    for (let i = 0; i < 40 && !code; i++) {
      await sleep(600);
      code = await page.evaluate(() => { const t = (document.querySelector("div[role=main]") || document.body).innerText; return (t.match(/\b\d{6}\b/) || [])[1] || ""; });
    }
    console.log("U2:", page.url().slice(0, 130));
    console.log("T2:", await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 300)));
    console.log("CODE:", code || "(none)");
  }
} finally { await browser.close(); }
