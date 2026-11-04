import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
function toks(html) {
  return {
    usi: g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html),
    at: g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html),
    region: g(/name="region"[^>]*value="([^"]*)"/, html) || "FR",
  };
}
async function inPost(params) {
  const d = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", ...params }) })).json();
  return String(d.request);
}
async function waitRes(id) {
  for (let i = 0; i < 30; i++) { await sleep(2500);
    const d = await (await fetch(`https://2captcha.com/res.php?key=${KEY}&action=get&id=${id}&json=1`)).json();
    if (d && d.status === 1 && d.request && d.request !== "NOT_FOUND") return String(d.request); }
  return "";
}
const SITEKEY = "6Lf-_ekqAAAAAO4AXrJISaHw4_bW76NcfwhLN7Is";
const GETU = "https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const E = "xbot0zdzcm55@gmail.com", P = "Xb-0zdzcm-5683";

const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
try {
  const p = await browser.newPage();
  await p.setUserAgent(UAS);
  await p.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
  await p.goto(GETU, { waitUntil: "networkidle2" });
  await sleep(1200);
  const html1 = await p.content();
  const t1 = toks(html1);
  const bg = await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: GETU, enterprise: "1" }));
  const ck = await browser.cookies();
  const jarS = ck.map((c) => `${c.name}=${c.value}`).join("; ");
  const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(t1.usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
  const H = { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded" };
  const p1 = await fetch(act, { method: "POST", headers: { ...H, cookie: jarS }, body: new URLSearchParams({ identifier: E, hiddenPassword: "", usi: t1.usi, domain: "", region: t1.region, bgresponse: bg, action: "1", at: t1.at }) });
  const h1 = await p1.text();
  console.log("S1:", p1.status, "| url:", decodeURIComponent(p1.url).slice(0, 130));
  console.log("S1 passwd:", /name="passwd"/.test(h1));
  const t2 = toks(h1);
  if (/name="passwd"/.test(h1)) {
    const bg2 = await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: act, enterprise: "1" }));
    const p2 = await fetch(act, { method: "POST", headers: { ...H, cookie: jarS }, body: new URLSearchParams({ PageNum: "2", passwd: P, at: t2.at, usi: t2.usi || t1.usi, domain: "", region: t2.region, bgresponse: bg2, action: "2" }) });
    const h2 = await p2.text();
    const body = h2.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
    console.log("S2:", p2.status, "code:", (body.match(/\b(\d{6})\b/) || [])[1] || "(none)");
    console.log("S2 txt:", body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 260));
  }
} finally { await browser.close(); }
