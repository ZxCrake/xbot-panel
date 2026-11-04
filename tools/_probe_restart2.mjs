const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
async function inPost(params) {
  const d = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", ...params }) })).json();
  return String(d.request);
}
async function waitRes(id) {
  for (let i = 0; i < 30; i++) { await new Promise((r) => setTimeout(r, 2500));
    const d = await (await fetch(`https://2captcha.com/res.php?key=${KEY}&action=get&id=${id}&json=1`)).json();
    if (d && d.status === 1 && d.request && d.request !== "NOT_FOUND") return String(d.request); }
  return "";
}
const SITEKEY = "6Lf-_ekqAAAAAO4AXrJISaHw4_bW76NcfwhLN7Is";
const E = "xbot1ivqi69@gmail.com";
const GETU = "https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
let r = await fetch(GETU, { headers: { "User-Agent": UAS } });
let html = await r.text(); absorb(r);
let at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
let usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
let bg = g(/name="bgresponse"[^>]*value="([^"]*)"/, html) || await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: GETU, enterprise: "1" }));
const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
let p = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: bg, action: "1", at }) });
let h = await p.text(); absorb(p);
const restart = decodeURIComponent((h.match(/href="(\/restart[^"]+)"/) || [])[1] || "").replace(/&amp;/g, "&");
console.log("restart:", restart.slice(0, 140));
const p2 = await fetch("https://accounts.google.com" + restart, { headers: { "User-Agent": UAS, cookie: jar.s } });
const h2 = await p2.text(); absorb(p2);
console.log("RESTART:", p2.status, "| inputs:", [...h2.matchAll(/<input[^>]*>/g)].map((m) => `${g(/name="([^"]*)"/, m[0])}=${g(/value="([^"]*)"/, m[0]).slice(0, 16)}`).join(" ; ").slice(0, 260));
const at2 = g(/name="at"[^>]*value="([^"]+)"/, h2) || g(/"SNlM0e":"([^"]+)"/, h2);
const usi2 = g(/name="usi"[^>]*value="([^"]+)"/, h2) || g(/"Qzxixc":"([^"]+)"/, h2);
const bg2 = g(/name="bgresponse"[^>]*value="([^"]*)"/, h2);
if (at2 && usi2) {
  const act2 = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi2)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
  const p3 = await fetch(act2, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ identifier: E, hiddenPassword: "", usi: usi2, domain: "", region: "FR", bgresponse: bg2 || bg, action: "1", at: at2 }) });
  const h3 = await p3.text(); absorb(p3);
  console.log("S2:", p3.status, "| passwd:", /name="passwd"/.test(h3), "| txt:", h3.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 180));
}
