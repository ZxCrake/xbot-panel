const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const E = "xbot0va4d53@gmail.com";
const r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: { "User-Agent": UA } });
let html = await r.text(); absorb(r);
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const p = await fetch(`https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: "", action: "1", at }) });
const h = await p.text(); absorb(p);
console.log("URL:", p.url);
console.log("status:", p.status);
const i = h.indexOf("jsdata");
console.log("jsdata-snippet:", h.slice(i, i + 900));
const j = h.indexOf("deferred");
console.log("deferred:", h.slice(j, j + 900));
