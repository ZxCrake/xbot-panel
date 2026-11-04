import puppeteer from "puppeteer";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
function toks(html) {
  return {
    usi: g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html),
    at: g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html),
    bg: g(/name="bgresponse"[^>]*value="([^"]*)"/, html),
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

const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }

const bg = await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: GETU, enterprise: "1" }));
console.log("bg len:", bg.length);
const r = await fetch(GETU, { headers: { "User-Agent": UAS } });
let html = await r.text(); absorb(r);
let t = toks(html);
const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(t.usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
async function post(b) {
  const p = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams(b) });
  const h = await p.text(); absorb(p);
  return h;
}
let h1 = await post({ identifier: E, hiddenPassword: "", usi: t.usi, domain: "", region: t.region, bgresponse: bg, action: "1", at: t.at });
console.log("S1 passwd:", /name="passwd"/.test(h1), "| txt:", h1.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 160));
t = toks(h1);
if (/name="passwd"/.test(h1)) {
  const bg2 = await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: act, enterprise: "1" }));
  let h2 = await post({ PageNum: "2", passwd: P, at: t.at, usi: t.usi || "", domain: "", region: t.region, bgresponse: bg2, action: "2" });
  const body = h2.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
  console.log("S2 txt:", body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 300));
  console.log("CODE:", (body.match(/\b(\d{6})\b/) || [])[1] || "(none)");
}
