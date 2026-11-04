import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"] });
try {
  const page = await browser.newPage();
  await page.goto("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await page.type("#identifierId", "xbot0uvl1d70@gmail.com", { delay: 25 });
  await page.evaluate(() => document.querySelector("#identifierNext").click());
  await sleep(3000);
  console.log("U1:", page.url().slice(0, 130));
  console.log("T1:", await page.evaluate(() => document.body.innerText.slice(0, 200)));
  const pw = await page.$("[name='passwd']");
  console.log("passwd input:", !!pw);
  if (pw) {
    await pw.type("Xb-0uvl1d-6329", { delay: 25 });
    await page.evaluate(() => {
      const n = document.querySelector("#passwordNext");
      if (n) n.click(); else [...document.querySelectorAll("button")].find((b) => /^(suivant|next)$/i.test((b.textContent || "").trim()))?.click();
    });
    await sleep(4000);
    console.log("U2:", page.url().slice(0, 130));
    const t = await page.evaluate(() => document.body.innerText.slice(0, 600));
    console.log("T2:", t);
    console.log("code:", (t.match(/\b\d{6}\b/) || [])[1] || "(none)");
  }
} finally { await browser.close(); }
