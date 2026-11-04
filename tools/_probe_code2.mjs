const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
function g(re, html) { return (re.exec(html) || [])[1] || ""; }
const email = "xbot0uvl1d70@gmail.com";
let r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: { "User-Agent": UA } });
let html = await r.text(); absorb(r);
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const region = g(/name="region"[^>]*value="([^"]*)"/, html);
const bg = g(/name="bgresponse"[^>]*value="([^"]*)"/, html);
console.log("GET usi:", usi, "at:", at.slice(0, 20), "bg:", bg.slice(0, 20), "region:", region);
const action = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
const p = await fetch(action, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ identifier: email, hiddenPassword: "", usi, domain: "", region, bgresponse: bg, action: "1", at }) });
const h = await p.text(); absorb(p);
console.log("POST:", p.status, "url:", p.url);
const i = h.indexOf("<body");
console.log(h.slice(i, i + 6000));
