const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
function g(re, html) { return (re.exec(html) || [])[1] || ""; }
const H = { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded" };
const email = "xbot0uvl1d70@gmail.com", password = "Xb-0uvl1d-6329";

let r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: H });
let html = await r.text(); absorb(r);
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const region = g(/name="region"[^>]*value="([^"]*)"/, html);

async function post(label, url, bodyObj) {
  const p = await fetch(url, { method: "POST", headers: { ...H, cookie: jar.s }, body: new URLSearchParams(bodyObj) });
  const h = await p.text(); absorb(p);
  console.log(label, p.status, "url:", p.url.slice(0, 100));
  console.log(label, "inputs:", [...h.matchAll(/<input[^>]*>/g)].map((m) => `${g(/name="([^"]*)"/, m[0])}=${g(/value="([^"]*)"/, m[0]).slice(0, 24)}`).join(" ; ").slice(0, 400));
  return h;
}

const act1 = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
html = await post("S1", act1, { identifier: email, hiddenPassword: "", usi, domain: "", region, bgresponse: g(/name="bgresponse"[^>]*value="([^"]*)"/, html), action: "1", at });
// S1 = page rejected : on reposte son propre <form>
const formAction = g(/action="([^"]+)"/, html);
const at2 = g(/name="at"[^>]*value="([^"]+)"/, html);
const clean = (u) => u.replace(/&amp;/g, "&");
html = await post("S2", clean("https://accounts.google.com" + formAction), { identifierInput: email, at: at2 });
const at3 = g(/name="at"[^>]*value="([^"]+)"/, html);
if (/name="passwd"/.test(html)) {
  html = await post("S3", clean("https://accounts.google.com" + g(/action="([^"]+)"/, html)), { passwd: password, at: at3, action: "2" });
  console.log("S3 text:", html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").slice(0, 400));
}
console.log("digits:", [...html.matchAll(/\b\d{6}\b/g)].map((m) => m[0]).slice(0, 6).join(","));
