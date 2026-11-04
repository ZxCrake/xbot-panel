import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const page = await browser.newPage();
  await page.setUserAgent(UAS);
  await page.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  page.on("response", async (rs) => {
    try {
      if (rs.request().method() === "POST" && rs.url().includes("batchexecute")) {
        console.log("RPC", rs.status(), "body:", (rs.request().postData() || "").slice(0, 260));
        console.log("   resp:", (await rs.text()).slice(0, 420).replace(/\n/g, " "));
      }
    } catch {}
  });
  await page.goto("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  console.log("inputs:", await page.evaluate(() => [...document.querySelectorAll("input")].map((i) => `${i.getAttribute("name") || i.id || "?"}=${(i.value || "").slice(0, 14)}`).join(" ; ")));
  await page.type("#identifierId", "xbot0w0iqh74@gmail.com", { delay: 25 });
  await page.evaluate(() => document.querySelector("#identifierNext").click());
  await sleep(3500);
  console.log("after-id url:", page.url().slice(0, 130));
  const pw = await page.$("[name='passwd']");
  console.log("passwd:", !!pw);
  if (pw) {
    await pw.type("Xb-0w0iqh-xxxx", { delay: 25 });
    await page.evaluate(() => document.querySelector("#passwordNext")?.click());
    await sleep(3500);
    console.log("after-pw url:", page.url().slice(0, 130));
    console.log("txt:", await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 260)));
  }
} finally { await browser.close(); }
