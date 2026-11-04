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
const E = "xbot0uvl1d70@gmail.com", P = "Xb-0uvl1d-6329";

let r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: { "User-Agent": UAS } });
let html = await r.text(); absorb(r);
let usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
let at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const H = { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded" };

async function step(n, bg, bodyObj) {
  const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
  const p = await fetch(act, { method: "POST", headers: { ...H, cookie: jar.s }, body: new URLSearchParams(bodyObj) });
  const h = await p.text(); absorb(p);
  console.log(n, p.status, "url:", decodeURIComponent(p.url).slice(0, 140));
  console.log(n, "inputs:", [...h.matchAll(/<input[^>]*>/g)].map((m) => `${g(/name="([^"]*)"/, m[0])}=${g(/value="([^"]*)"/, m[0]).slice(0, 16)}`).join(" ; ").slice(0, 260));
  return h;
}

let bg = await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: "https://accounts.google.com/v3/signin/identifier", enterprise: "1" }));
let h1 = await step("S1", bg, { identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: bg, action: "1", at });
// S2 : page rejected -> re-POST via identifierInput + nouveau at
const at2 = g(/name="at"[^>]*value="([^"]+)"/, h1);
let h2 = await step("S2", bg, { identifierInput: E, at: at2, action: "1" });
// si passwd
if (/name="passwd"/.test(h2)) {
  const at3 = g(/name="at"[^>]*value="([^"]+)"/, h2);
  const usi3 = g(/name="usi"[^>]*value="([^"]+)"/, h2) || usi;
  const h3 = await step("S3", bg, { PageNum: "2", passwd: P, at: at3, usi: usi3, domain: "", region: "FR", bgresponse: bg, action: "2" });
  const body = h3.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
  console.log("CODE:", (body.match(/\b(\d{6})\b/) || [])[1] || "(none)");
}
