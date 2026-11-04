const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
const API = "https://2captcha.com";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
async function inPost(params) {
  const d = await (await fetch(`${API}/in.php`, { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", ...params }) })).json();
  return String(d.request);
}
async function waitRes(id) {
  for (let i = 0; i < 40; i++) { await new Promise((r) => setTimeout(r, 2500));
    const d = await (await fetch(`${API}/res.php?key=${KEY}&action=get&id=${id}&json=1`)).json();
    if (d && d.status === 1 && d.request && d.request !== "NOT_FOUND") return String(d.request); }
  return "";
}
const jar = { s: "" };
const absorb = (r) => { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; };
const E = "xbot0w4mxj6@gmail.com", P = "Xb-0w4mxj-3063";
const GETU = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin";
const r = await fetch(GETU, { headers: { "User-Agent": UAS } });
const html = await r.text(); absorb(r);
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html);
const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const anchor = [...html.matchAll(/recaptcha\/enterprise[^"'\s]*/g)].map((m) => m[0]);
console.log("anchors:", anchor.length, anchor[0] ? anchor[0].slice(0, 200) : "");
const k = (anchor[0] || "").match(/[?&]k=([-\w]+)/);
let bg = "js_disabled";
if (k) {
  const id = await inPost({ method: "userrecaptcha", googlekey: k[1], pageurl: GETU, enterprise: "1" });
  bg = await waitRes(id);
  console.log("sitekey:", k[1], "bg len:", bg.length);
}
const act = `https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&dsh=${encodeURIComponent(usi)}&emr=1&flowEntry=ServiceLogin&flowName=WebLiteSignIn&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail`;
const p1 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: bg, pstMsg: "1", checkConnection: "youtube:337", checkedDomains: "youtube", action: "1", at }) });
const h1 = await p1.text(); absorb(p1);
console.log("id1:", p1.status, decodeURIComponent(p1.url).slice(0, 150));
console.log("has passwd:", /name="passwd"/.test(h1));
if (/name="passwd"/.test(h1)) {
  const at2 = g(/name="at"[^>]*value="([^"]+)"/, h1) || g(/"SNlM0e":"([^"]+)"/, h1);
  const bg2 = g(/name="bgresponse"[^>]*value="([^"]*)"/, h1) || bg;
  const p2 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ PageNum: "2", passwd: P, at: at2, action: "2", usi, domain: "", region: "FR", bgresponse: bg2 }) });
  const h2 = await p2.text();
  const body = h2.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
  console.log("id2:", p2.status, decodeURIComponent(p2.url).slice(0, 150));
  console.log("CODE:", (body.match(/\b(\d{6})\b/) || [])[1] || "(none)");
  console.log("txt:", body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 400));
}
