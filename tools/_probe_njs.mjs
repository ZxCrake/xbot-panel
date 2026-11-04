const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const E = "xbot2h02n64@gmail.com", P = "Xb-2h02n6-9075";
const H = { "User-Agent": UAS };

// 1) GET identifier avec hl=fr pour voir si le no-js rend at/ct avec valeur
const r = await fetch("https://accounts.google.com/v3/signin/identifier?nojs=1&hl=fr&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: H });
const html = await r.text();
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html);
const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
const ct = g(/name="ct"[^>]*value="([^"]+)"/, html);
console.log("nojs: usi=", usi.slice(0, 12), "at=", at.slice(0, 12), "ct=", ct.slice(0, 12));

// 2) POST avec ct (si valeur)
const jar = { s: "" };
function absorb(x) { for (const c of (x.headers.getSetCookie ? x.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
absorb(r);
const act = `https://accounts.google.com/v3/signin/identifier?nojs=1&hl=fr&dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
const p1 = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ PageNum: "1", identifier: E, hiddenPassword: "", usi, domain: "", region: "FR", action: "1", at, ct }) });
const h1 = await p1.text(); absorb(p1);
console.log("POST:", p1.status, "url:", decodeURIComponent(p1.url).slice(0, 140));
console.log("inputs:", [...h1.matchAll(/<input[^>]*>/g)].map((m) => `${g(/name="([^"]*)"/, m[0])}=${g(/value="([^"]*)"/, m[0]).slice(0, 16)}`).join(" ; ").slice(0, 260));

// 3) variante passive=1209600 + osid sans nojs
const r3 = await fetch("https://accounts.google.com/v3/signin/identifier?osid=1&passive=1209600&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&hl=fr&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { headers: H });
const h3 = await r3.text();
const usi3 = g(/name="usi"[^>]*value="([^"]+)"/, h3) || g(/"Qzxixc":"([^"]+)"/, h3);
const at3 = g(/name="at"[^>]*value="([^"]+)"/, h3) || g(/"SNlM0e":"([^"]+)"/, h3);
console.log("osid GET: at=", at3.slice(0, 12), "usi=", usi3.slice(0, 12));
const p3 = await fetch(`https://accounts.google.com/v3/signin/identifier?osid=1&passive=1209600&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&hl=fr&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin&dsh=${encodeURIComponent(usi3)}`, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams({ identifier: E, hiddenPassword: "", usi: usi3, domain: "", region: "FR", bgresponse: "js_disabled", pstMsg: "1", checkConnection: "youtube:337", checkedDomains: "youtube", action: "1", at: at3 }) });
const h4 = await p3.text();
console.log("osid POST:", p3.status, "url:", decodeURIComponent(p3.url).slice(0, 140), "passwd:", /name="passwd"/.test(h4));
