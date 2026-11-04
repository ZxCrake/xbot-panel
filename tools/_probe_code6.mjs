import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"] });
try {
  const page = await browser.newPage();
  await page.goto("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await page.type("#identifierId", "xbot0v3jzf49@gmail.com", { delay: 25 });
  await page.evaluate(() => document.querySelector("#identifierNext").click());
  for (let i = 0; i < 20; i++) { await sleep(500); if (await page.$("[name='passwd']")) break; }
  console.log("U1:", page.url().slice(0, 120));
  console.log("T1:", (await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 260))));
  const pw = await page.$("[name='passwd']");
  if (pw) {
    await pw.type("Xb-0v3jzf-1286", { delay: 25 });
    await page.evaluate(() => document.querySelector("#passwordNext")?.click());
    for (let i = 0; i < 30; i++) { await sleep(500);
      const t = await page.evaluate(() => document.body.innerText);
      if (/\b\d{6}\b/.test(t) && /gmail\.com/.test(t)) { console.log("U2:", page.url().slice(0, 120)); console.log("code:", (t.match(/\b\d{6}\b/) || [])[1]); console.log("T2:", t.replace(/\n+/g, " | ").slice(0, 400)); break; }
    }
  }
} finally { await browser.close(); }
