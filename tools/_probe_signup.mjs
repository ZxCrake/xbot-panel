import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"] });
try {
  const page = await browser.newPage();
  await page.goto("https://accounts.google.com/signup", { waitUntil: "networkidle2" });
  const dump = async (label) => {
    const st = await page.evaluate(() => ({
      url: location.href,
      inputs: [...document.querySelectorAll("input")].map((i) => `${i.id || "-"}|${i.getAttribute("name") || "-"}|${i.getAttribute("jsname") || "-"}`),
      btns: [...document.querySelectorAll("button")].map((b) => (b.textContent || "").trim()).filter(Boolean),
      lis: [...document.querySelectorAll("li")].map((l) => (l.textContent || "").trim()).slice(0, 14),
      opt: [...document.querySelectorAll("[role=option]")].map((l) => (l.textContent || "").trim()).slice(0, 14),
    }));
    console.log("==", label, JSON.stringify(st, null, 1));
  };
  await dump("P0");
  const stamp = Date.now().toString(36).slice(-6);
  const prefix = "xbot" + stamp + Math.floor(Math.random() * 90);
  const email = `${prefix}@gmail.com`;
  const password = `Xb-${stamp}-${Math.floor(Math.random() * 9000 + 1000)}`;
  console.log("email:", email, "pass:", password);

  await page.type("#firstName", "Xbot", { delay: 25 });
  await page.type("#lastName", stamp, { delay: 25 });
  await page.evaluate(() => { const b = [...document.querySelectorAll("button")].find((x) => /^(suivant|next)$/i.test((x.textContent || "").trim())); if (b) b.click(); });
  await sleep(2000);
  await dump("P1-nom");

  await page.type("#day", "15", { delay: 25 });
  await page.type("#year", "1990", { delay: 25 });
  await page.evaluate(() => {
    const m = [...document.querySelectorAll("input")].find((i) => !i.id && i.getAttribute("jsname") === "YPqjbf");
    if (m) { m.click(); m.focus(); }
  });
  await sleep(800);
  await dump("P2-mois-ouvert");
  await page.evaluate(() => {
    const o = [...document.querySelectorAll("li[role=option],li")].find((l) => /^janvier$/i.test((l.textContent || "").trim()));
    if (o) o.click();
  });
  await sleep(600);
  await page.evaluate(() => {
    const el = [...document.querySelectorAll("li,[role=option]")].find((x) => /^(homme|male)$/i.test((x.textContent || "").trim()));
    if (el) el.click();
  });
  await sleep(600);
  await dump("P2-apres-choix");
  await page.evaluate(() => { const b = [...document.querySelectorAll("button")].find((x) => /^(suivant|next)$/i.test((x.textContent || "").trim())); if (b) b.click(); });
  await sleep(2200);
  if (!(await page.$("#emailPhone"))) await page.evaluate(() => { const b = [...document.querySelectorAll("button")].find((x) => /^(suivant|next)$/i.test((x.textContent || "").trim())); if (b) b.click(); });
  await sleep(1800);
  await dump("P3-email");

  if (await page.$("#emailPhone")) await page.type("#emailPhone", email, { delay: 25 });
  await sleep(500);
  await dump("P3b-tape");
  await page.evaluate(() => { const b = [...document.querySelectorAll("button")].find((x) => /^(suivant|next)$/i.test((x.textContent || "").trim())); if (b) b.click(); });
  await sleep(2500);
  await dump("P4-apres-email");
  console.log("iframes:", await page.evaluate(() => [...document.querySelectorAll("iframe")].map((f) => f.getAttribute("src"))));
  console.log("body-text:", await page.evaluate(() => document.body.innerText.slice(0, 400)));
} finally {
  await browser.close();
}
