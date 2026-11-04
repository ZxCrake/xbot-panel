import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const API = "https://2captcha.com";
async function inPost(params) {
  const res = await fetch(`${API}/in.php`, { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", ...params }) });
  const d = await res.json(); return String(d.request);
}
async function waitRes(id) {
  for (let i = 0; i < 40; i++) { await sleep(2500);
    const d = await (await fetch(`${API}/res.php?key=${KEY}&action=get&id=${id}&json=1`)).json();
    if (d && d.status === 1 && d.request && d.request !== "NOT_FOUND") return String(d.request);
  } return "";
}
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"] });
try {
  const page = await browser.newPage();
  await page.goto("https://accounts.google.com/signup", { waitUntil: "networkidle2" });
  const stamp = Date.now().toString(36).slice(-6);
  const email = `xbot${stamp}${Math.floor(Math.random() * 90)}@gmail.com`;
  const password = `Xb-${stamp}-${Math.floor(Math.random() * 9000 + 1000)}`;
  console.log("email:", email, password);
  const next = async () => page.evaluate(() => { const b = [...document.querySelectorAll("button")].find((x) => /^(suivant|next)$/i.test((x.textContent || "").trim())); if (b) b.click(); });
  const dump = async (l) => console.log("==", l, "URL:", page.url().slice(0, 100), "\n TXT:", (await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 300))));

  await page.waitForSelector("#firstName"); await page.type("#firstName", "Xbot"); await page.type("#lastName", stamp);
  await next(); await sleep(1500); await dump("apres nom");
  await page.type("#day", "15"); await page.type("#year", "1990");
  await page.evaluate(() => { const m = [...document.querySelectorAll("input")].find((i) => !i.id && i.getAttribute("jsname") === "YPqjbf"); if (m) { m.click(); m.focus(); } });
  await sleep(700);
  await page.evaluate(() => { const o = [...document.querySelectorAll("li[role=option],li")].find((l) => /^janvier$/i.test((l.textContent || "").trim())); if (o) o.click(); });
  await sleep(400);
  await page.evaluate(() => { const el = [...document.querySelectorAll("li,[role=option]")].find((x) => /^(homme|male)$/i.test((x.textContent || "").trim())); if (el) el.click(); });
  await sleep(400); await next(); await sleep(1800);
  if (!(await page.$("#emailPhone"))) await next(); await sleep(1800); await dump("apres anniversaire");
  await page.type("#emailPhone", email); await sleep(800); await next(); await sleep(2500); await dump("apres email/captcha");
  // 2e passe captcha si iframe
  const src = await page.evaluate(() => { const f = [...document.querySelectorAll("iframe")].map((x) => x.getAttribute("src")).find((s) => s && s.includes("recaptcha")); return f || ""; });
  if (src) {
    const sitekey = (src.match(/[?&]k=([-\w]+)/) || [])[1];
    console.log("sitekey:", sitekey);
    const token = await waitRes(await inPost({ method: "userrecaptcha", googlekey: sitekey, pageurl: page.url(), enterprise: "1" }));
    console.log("token len:", token.length);
    await page.evaluate((t) => { for (const ta of document.querySelectorAll("#g-recaptcha-response,[name='g-recaptcha-response']")) ta.value = t; const idoc = document.querySelector("iframe").contentDocument; const i2 = idoc && idoc.getElementById("g-recaptcha-response"); if (i2) i2.value = t; }, token);
    await next(); await sleep(2500); await dump("apres token");
  }
  const codeIn = await page.$("[name='code']");
  console.log("code input:", !!codeIn);
  if (codeIn) {
    await codeIn.type("303030", { delay: 25 });
    await next(); await sleep(2500); await dump("apres code 303030");
  }
} finally { await browser.close(); }
