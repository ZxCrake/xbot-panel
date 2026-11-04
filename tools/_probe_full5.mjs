const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const E = "xbot0vjei070@gmail.com", P = "Xb-0vjei0-9641";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
function txt(h) { return h.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 320); }
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
const H = { "User-Agent": UA };

let r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: H });
let html = await r.text(); absorb(r);
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
async function post(b) {
  const p = await fetch(act, { method: "POST", headers: { ...H, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams(b) });
  const h = await p.text(); absorb(p);
  console.log("-- POST", p.status, "url:", decodeURIComponent(p.url).slice(0, 140));
  console.log("   txt:", txt(h));
  console.log("   inputs:", [...h.matchAll(/<input[^>]*>/g)].map((m) => `${g(/name="([^"]*)"/, m[0])}=${g(/value="([^"]*)"/, m[0]).slice(0, 16)}`).join(" ; ").slice(0, 300));
  return h;
}
let h1 = await post({ identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: "", action: "1", at });
// itération 2 avec le même jar
r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: H });
html = await r.text(); absorb(r);
const at2 = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
let h2 = await post({ identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: "", action: "1", at: at2 });
if (/name="passwd"/.test(h2)) {
  const at3 = g(/name="at"[^>]*value="([^"]+)"/, h2) || g(/"SNlM0e":"([^"]+)"/, h2);
  const h3 = await post({ passwd: P, at: at3, action: "2" });
  const m = h3.match(/\b(\d{6})\b/);
  console.log("CODE:", m ? m[1] : "(none in 3)");
}
