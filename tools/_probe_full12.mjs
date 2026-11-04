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
      const u = rs.url();
      if (u.includes("/_/") || u.includes("task.json") || /lifecycle/.test(u)) {
        const t = await rs.text();
        console.log("RESP", rs.status(), u.slice(0, 110), "\n  ", t.slice(0, 500).replace(/\n/g, " "));
      }
    } catch {}
  });
  await page.goto("https://accounts.google.com/lifecycle/steps/signup/name", { waitUntil: "networkidle2" });
  console.log("inputs:", await page.evaluate(() => [...document.querySelectorAll("input")].map((i) => `${i.getAttribute("name") || i.id || "?"}=${(i.value || "").slice(0, 14)}`).join(" ; ")));
} finally { await browser.close(); }
