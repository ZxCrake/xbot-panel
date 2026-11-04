const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
async function inPost(params) {
  const d = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: new URLSearchParams({ key: KEY, json: "1", ...params }) })).json();
  return String(d.request);
}
async function waitRes(id) {
  for (let i = 0; i < 40; i++) { await new Promise((r) => setTimeout(r, 2500));
    const d = await (await fetch(`https://2captcha.com/res.php?key=${KEY}&action=get&id=${id}&json=1`)).json();
    if (d && d.status === 1 && d.request && d.request !== "NOT_FOUND") return String(d.request); }
  return "";
}
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
const H = { "User-Agent": UA };
const E = process.argv[2] || "xbot0x9f9i3@gmail.com", P = process.argv[3] || "Xb-0x9f9i-7601";
const GETU = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin";
let r = await fetch(GETU, { headers: H });
let html = await r.text(); absorb(r);
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html);
const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const bg = await waitRes(await inPost({ method: "userrecaptcha", googlekey: "6Lf-_ekqAAAAAO4AXrJISaHw4_bW76NcfwhLN7Is", pageurl: GETU, enterprise: "1" }));
console.log("bg len:", bg.length);
const act = `https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&dsh=${encodeURIComponent(usi)}&emr=1&flowEntry=ServiceLogin&flowName=WebLiteSignIn&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail`;
const p1 = await fetch(act, { method: "POST", headers: { ...H, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: bg, pstMsg: "1", checkConnection: "youtube:337", checkedDomains: "youtube", action: "1", at }) });
html = await p1.text(); absorb(p1);
console.log("S1:", p1.status, decodeURIComponent(p1.url).slice(0, 130));
console.log("passwd:", /name="passwd"/.test(html), "| txt:", html.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 200));
if (/name="passwd"/.test(html)) {
  const at2 = g(/name="at"[^>]*value="([^"]+)"/, html);
  const usi2 = g(/name="usi"[^>]*value="([^"]+)"/, html) || usi;
  const bg2 = await waitRes(await inPost({ method: "userrecaptcha", googlekey: "6Lf-_ekqAAAAAO4AXrJISaHw4_bW76NcfwhLN7Is", pageurl: act, enterprise: "1" }));
  const p2 = await fetch(act, { method: "POST", headers: { ...H, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ PageNum: "2", passwd: P, at: at2, usi: usi2, region: "FR", domain: "", hiddenPassword: "", bgresponse: bg2, action: "2" }) });
  const h2 = await p2.text(); absorb(p2);
  const body = h2.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
  console.log("S2:", p2.status, decodeURIComponent(p2.url).slice(0, 130));
  console.log("CODE:", (body.match(/\b(\d{6})\b/) || [])[1] || "(none)");
  console.log("txt:", body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 300));
}
