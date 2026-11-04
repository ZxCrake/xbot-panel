import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"] });
async function nojsProbe(E, P, jarS, at, usi) {
  const variants = [
    ["bg-vide", { identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: "", action: "1", at }],
    ["avec-nojs", { identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: "", action: "1", at, nojs: "1" }],
    ["js_dis", { identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: "js_disabled", action: "1", at }],
  ];
  for (const [label, obj] of variants) {
    const p = await fetch(`https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jarS }, body: new URLSearchParams(obj) });
    const h = await p.text();
    const url = decodeURIComponent(p.url);
    const txt = h.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    console.log(label, "->", p.status, "rrk:", (url.match(/rrk=(\d+)/) || [])[1] || "?", "idnf:", /idnf=/.test(url), "| passwd:", /name="passwd"/.test(h), "| code:", ((txt.match(/\b\d{6}\b/) || [])[1] || ""));
  }
}
try {
  const p1 = await browser.newPage();
  await p1.setUserAgent(UAS);
  await p1.goto("https://accounts.google.com/v3/signin/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "domcontentloaded" });
  const vals = await p1.evaluate(() => { const o = {}; for (const i of document.querySelectorAll("input")) { const n = i.getAttribute("name") || i.id; if (n) o[n] = i.value || ""; } return o; });
  const ck = await browser.cookies();
  const jarS = ck.map((c) => `${c.name}=${c.value}`).join("; ");
  console.log("nojs inputs:", JSON.stringify(Object.fromEntries(Object.entries(vals).map(([k, v]) => [k, String(v).slice(0, 12)]))));
  await nojsProbe("xbot0y2u8155@gmail.com", "Xb-0y2u81-7139", jarS, g(/"SNlM0e":"([^"]+)"/, await p1.content()), vals.usi || "");
} finally { await browser.close(); }
