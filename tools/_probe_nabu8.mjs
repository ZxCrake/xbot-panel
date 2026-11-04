const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const KEY = "b1147a35362c7fb3aca8c2e2630c412e";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const GETU = "https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const SITEKEY = "6Lf-_ekqAAAAAO4AXrJISaHw4_bW76NcfwhLN7Is";

// 1) token d'ancre : 1re passe via iframe? et 2e via reload direct
const r0 = await fetch(GETU, { headers: { "User-Agent": UAS } });
const html0 = await r0.text();
const at = g(/name="at"[^>]*value="([^"]+)"/, html0) || g(/"SNlM0e":"([^"]+)"/, html0);
const usi = g(/name="usi"[^>]*value="([^"]+)"/, html0) || g(/"Qzxixc":"([^"]+)"/, html0);
let jar = "";
for (const c of (r0.headers.getSetCookie ? r0.headers.getSetCookie() : [])) jar += (jar ? "; " : "") + c.split(";")[0];

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
const bg = await waitRes(await inPost({ method: "userrecaptcha", googlekey: SITEKEY, pageurl: GETU, enterprise: "1" }));

const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;

// A) POST avec le bg résolu via 2captcha
let p = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body: new URLSearchParams({ identifier: "xbot0zdzcm55@gmail.com", hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: bg, action: "1", at }) });
let t = await p.text();
console.log("A:", p.status, "rrk:", (decodeURIComponent(p.url).match(/rrk=(\d+)/) || [])[1], "idnf:", /idnf=/.test(decodeURIComponent(p.url)), "passwd:", /name="passwd"/.test(t));

// B) POST avec le token du reload (celui que le JS injecte dans bgresponse)
const m = html0.match(/data:\[\["rresp","([^"]+)"/) || html0.match(/\["rresp","([^"]+)"/);
console.log("inline rresp:", m ? m[1].slice(0, 20) + "…" : "(none)");
if (m) {
  p = await fetch(act, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body: new URLSearchParams({ identifier: "xbot0zdzcm55@gmail.com", hiddenPassword: "", usi, domain: "", region: "FR", bgresponse: m[1], action: "1", at }) });
  t = await p.text();
  console.log("B:", p.status, "rrk:", (decodeURIComponent(p.url).match(/rrk=(\d+)/) || [])[1], "idnf:", /idnf=/.test(decodeURIComponent(p.url)), "passwd:", /name="passwd"/.test(t));
}
