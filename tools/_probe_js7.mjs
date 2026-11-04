import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
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
const E = "xbot0uvl1d70@gmail.com", P = "Xb-0uvl1d-6329";

const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
const GETU = "https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
let r = await fetch(GETU, { headers: { "User-Agent": UAS } });
let html = await r.text(); absorb(r);
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const region = g(/name="region"[^>]*value="([^"]*)"/, html) || "FR";
console.log("GET:", "usi", !!usi, "at", !!at, "region", region);

const bg = await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: GETU, enterprise: "1" }));
console.log("bg len:", bg.length);
const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
const H = { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded" };
let p1 = await fetch(act, { method: "POST", headers: { ...H, cookie: jar.s }, body: new URLSearchParams({ identifier: E, hiddenPassword: "", usi, domain: "", region, bgresponse: bg, action: "1", at }) });
let h1 = await p1.text();
console.log("S1:", p1.status, "url:", decodeURIComponent(p1.url).slice(0, 150));
console.log("passwd:", /name="passwd"/.test(h1), "| inputs:", [...h1.matchAll(/<input[^>]*>/g)].map((m) => `${g(/name="([^"]*)"/, m[0])}`).join(",").slice(0, 200));
