const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
function toks(html) {
  const g = (re) => (re.exec(html) || [])[1] || "";
  return {
    usi: g(/name="usi"[^>]*value="([^"]+)"/) || g(/"Qzxixc":"([^"]+)"/),
    at: g(/name="at"[^>]*value="([^"]+)"/) || g(/"SNlM0e":"([^"]+)"/),
    bg: g(/name="bgresponse"[^>]*value="([^"]*)"/),
    region: g(/name="region"[^>]*value="([^"]*)"/) || "FR",
  };
}
const email = "xbot0uvl1d70@gmail.com", password = "Xb-0uvl1d-6329";
let r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: { "User-Agent": UA } });
let html = await r.text(); absorb(r);
let t = toks(html);
const action = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(t.usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
async function step(bodyObj) {
  const p = await fetch(action, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body: new URLSearchParams(bodyObj) });
  const h = await p.text(); absorb(p);
  console.log("POST ->", p.status, "url:", p.url.slice(0, 90));
  return h;
}
html = await step({ identifier: email, hiddenPassword: "", usi: t.usi, domain: "", region: t.region, bgresponse: t.bg, action: "1", at: t.at });
t = toks(html);
console.log("page2 has passwd:", /name="passwd"/.test(html), "at2:", t.at.slice(0, 16));
html = await step({ passwd: password, at: t.at, action: "2" });
t = toks(html);
console.log("page3 first 500:", html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").slice(0, 500));
console.log("page3 digits6:", [...html.matchAll(/\b\d{6}\b/g)].map((m) => m[0]).slice(0, 8).join(","));
const m = /https:\/\/mail\.google\.com[^"'<> ]*/.exec(html);
console.log("mail url:", m && m[0].slice(0, 120));
if (m) {
  const p2 = await fetch(m[0], { headers: { "User-Agent": UA, cookie: jar.s } });
  const h2 = await p2.text();
  console.log("mail page:", p2.status, "len", h2.length);
  console.log("mail text 700:", h2.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").slice(0, 700));
  console.log("mail digits6:", [...h2.matchAll(/\b\d{6}\b/g)].map((x) => x[0]).slice(0, 10).join(","));
}
