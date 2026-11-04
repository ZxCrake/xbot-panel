const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const E = "xbot0uvl1d70@gmail.com", P = "Xb-0uvl1d-6329";

const GETU = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
let r = await fetch(GETU, { headers: { "User-Agent": UA } });
let html = await r.text(); absorb(r);
console.log("status:", r.status);
console.log("forms:", [...html.matchAll(/<form[^>]*>/g)].map((m) => m[0]).join(" ~ ").slice(0, 300));
console.log("inputs:", [...html.matchAll(/<input[^>]*>/g)].map((m) => m[0].replace(/\s+/g, " ").slice(0, 170)).join("\n  "));
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const region = g(/name="region"[^>]*value="([^"]*)"/, html);
const bg = g(/name="bgresponse"[^>]*value="([^"]*)"/, html);
console.log("usi:", usi, "at:", at.slice(0, 18), "bg len:", bg.length);

async function post(label, url, bodyObj) {
  const p = await fetch(url, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams(bodyObj) });
  const h = await p.text(); absorb(p);
  console.log("==", label, p.status, "url:", p.url.slice(0, 120));
  console.log(label, "inputs:", [...h.matchAll(/<input[^>]*>/g)].map((m) => `${g(/name="([^"]*)"/, m[0])}=${g(/value="([^"]*)"/, m[0]).slice(0, 18)}`).join(" ; ").slice(0, 300));
  console.log(label, "text:", h.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 250));
  return h;
}
const ACT = GETU.replace("GlifWebSignIn", "WebLiteSignIn") + "&dsh=" + encodeURIComponent(usi);
html = await post("S1-id", ACT, { identifier: E, hiddenPassword: "", usi, domain: "", region, bgresponse: bg, action: "1", at });
const at2 = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
if (/name="passwd"/.test(html)) {
  html = await post("S2-pass", ACT, { passwd: P, at: at2, action: "2" });
}
