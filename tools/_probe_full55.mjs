import puppeteer from "puppeteer-extra";
import Stealth from "puppeteer-extra-plugin-stealth";
puppeteer.use(Stealth());
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
async function inPost(params) {
  const d = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", ...params }) })).json();
  return String(d.request);
}
async function waitRes(id) {
  for (let i = 0; i < 20; i++) { await sleep(2000);
    const d = await (await fetch(`https://2captcha.com/res.php?key=${KEY}&action=get&id=${id}&json=1`)).json();
    if (d && d.status === 1 && d.request && d.request !== "NOT_FOUND") return String(d.request); }
  return "";
}
const SITEKEY = "6Lf-_ekqAAAAAO4AXrJISaHw4_bW76NcfwhLN7Is";
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"] });
try {
  const page = await browser.newPage();
  await page.setUserAgent(UAS);
  await page.goto("https://accounts.google.com/signup", { waitUntil: "networkidle2" });
  const stamp = Date.now().toString(36).slice(-6);
  const email = `xbot${stamp}${Math.floor(Math.random() * 90)}@gmail.com`;
  const password = `Xb-${stamp}-${Math.floor(Math.random() * 9000 + 1000)}`;
  console.log("email:", email, "pass:", password);
  const next = async () => page.evaluate(() => { const b = [...document.querySelectorAll("button")].find((x) => /^(suivant|next|passer|skip)$/i.test((x.textContent || "").trim())); if (b) b.click(); });
  const txt = async (l) => console.log(l, "::", await page.evaluate(() => document.body.innerText.replace(/\n+/g, " | ").slice(0, 160)));
  await page.waitForSelector("#firstName");
  await page.type("#firstName", "Xbot"); await page.type("#lastName", stamp); await next(); await sleep(1600); await txt("P1");
  await page.type("#day", "15"); await page.type("#year", "1990");
  await page.evaluate(() => { const m = [...document.querySelectorAll("input")].find((i) => !i.id && i.getAttribute("jsname") === "YPqjbf"); if (m) { m.click(); m.focus(); } });
  await sleep(500);
  await page.evaluate(() => { const o = [...document.querySelectorAll("li[role=option],li")].find((l) => /^jan(uary|vier)$/i.test((l.textContent || "").trim())); if (o) o.click(); });
  await sleep(300);
  await page.evaluate(() => { const el = [...document.querySelectorAll("li,[role=option]")].find((x) => /^(homme|male)$/i.test((x.textContent || "").trim())); if (el) el.click(); });
  await sleep(300); await next(); await sleep(1600);
  if (!(await page.$("#emailPhone"))) await next(); await sleep(1600); await txt("P2");
  await page.type("#emailPhone", email); await next(); await sleep(2200); await txt("P3");
  const src = await page.evaluate(() => { const f = [...document.querySelectorAll("iframe")].map((x) => x.getAttribute("src")).find((s) => s && s.includes("recaptcha")); return f || ""; });
  if (src) {
    const token = await waitRes(await inPost({ method: "userrecaptcha", googlekey: (src.match(/[?&]k=([-\w]+)/) || [])[1], pageurl: page.url(), enterprise: "1" }));
    await page.evaluate((t) => { for (const ta of document.querySelectorAll("#g-recaptcha-response,[name='g-recaptcha-response']")) ta.value = t; const i2 = document.querySelector("iframe")?.contentDocument?.getElementById("g-recaptcha-response"); if (i2) i2.value = t; }, token);
    await next(); await sleep(2200); await txt("P3b");
  }
  console.log("input code present:", !!(await page.$("[name='code']")));

  // lecture du code via pages rendues (même navigateur)
  const p2 = await browser.newPage();
  await p2.setUserAgent(UAS);
  let code = "";
  for (let i = 0; i < 12 && !code; i++) {
    await p2.goto("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
    await sleep(600);
    const h = await p2.content();
    const usi = g(/name="usi"[^>]*value="([^"]+)"/, h) || g(/"Qzxixc":"([^"]+)"/, h);
    const at = g(/name="at"[^>]*value="([^"]+)"/, h) || g(/"SNlM0e":"([^"]+)"/, h);
    const bg = await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: "https://accounts.google.com/v3/signin/identifier", enterprise: "1" }));
    const ck = (await browser.cookies()).map((c) => `${c.name}=${c.value}`).join("; ");
    const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
    const H = { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: ck };
    const p1r = await fetch(act, { method: "POST", headers: H, body: new URLSearchParams({ identifier: email, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: bg, action: "1", at }) });
    const h1 = await p1r.text();
    if (!/name="passwd"/.test(h1)) { console.log("iter", i + 1, "S1:", decodeURIComponent(p1r.url).slice(0, 60)); await sleep(2500); continue; }
    const at2 = g(/name="at"[^>]*value="([^"]+)"/, h1);
    const p2r = await fetch(act, { method: "POST", headers: H, body: new URLSearchParams({ PageNum: "2", passwd: password, at: at2, usi, domain: "", region: "FR", bgresponse: bg, action: "2" }) });
    const h2 = await p2r.text();
    const body = h2.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
    code = (body.match(/\b(\d{6})\b/) || [])[1] || "";
    console.log("iter", i + 1, "S2:", p2r.status, "code:", code || "(none)");
    await sleep(2000);
  }
  console.log("CODE:", code || "(none)");
  if (code) {
    await (await page.$("[name='code']")).type(code, { delay: 25 });
    await next(); await sleep(2500); await txt("FINAL");
    console.log("inputs final:", await page.evaluate(() => [...document.querySelectorAll("input")].map((i) => `${i.getAttribute("name") || i.id || i.getAttribute("jsname")}`).join(",")));
    console.log("btns final:", await page.evaluate(() => [...document.querySelectorAll("button")].map((b) => (b.textContent || "").trim()).filter(Boolean).join(" / ")));
  }
} finally { await browser.close(); }
