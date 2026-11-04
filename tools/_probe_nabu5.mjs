const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
const GETU = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin";
const r = await fetch(GETU, { headers: { "User-Agent": UAS } });
const html = await r.text(); absorb(r);
const at = g(/name="at" value="([^"]+)"/, html);
const dsh = g(/name="usi" value="([^"]+)"/, html);
const region = g(/name="region" value="([^"]+)"/, html) || "FR";
const bl = (html.match(/boq-identity\.[\w.-]+/g) || [])[0] || "";
const E = "xbot0y2u8155@gmail.com";
console.log("at:", at.slice(0, 16), "dsh:", dsh.slice(0, 14), "bl:", bl.split(".L.")[0]);
const url = `https://accounts.google.com/v3/signin/_/AccountsSignInUi/data/batchexecute?rpcids=NABu5d&source-path=%2Fv3%2Fsignin%2Fidentifier&f.sid=1&bl=${encodeURIComponent(bl)}&hl=fr&_reqid=1&rt=c`;
async function call(label, req) {
  const body = "f.req=" + encodeURIComponent(JSON.stringify(req)) + "&at=" + encodeURIComponent(at) + "&";
  const p = await fetch(url, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body });
  const t = await p.text();
  console.log("\n[", label, "]", p.status, t.slice(0, 700).replace(/\n/g, " "));
}
await call("A", [[["NABu5d", JSON.stringify([null, [["identifier", E], ["hiddenPassword", ""], ["usi", dsh], ["domain", ""], ["region", region], ["bgresponse", ""], ["action", "1"], ["at", at]]]), null, "generic"]]]);
await call("B", [[["NABu5d", JSON.stringify([null, [["identifier", E]], 1]), null, "1"]]]);
await call("C", [[["NABu5d", JSON.stringify([null, [["identifier", E], ["hiddenPassword", ""], ["usi", dsh], ["domain", ""], ["region", region]], 1, [], {}]), null, "generic"]]]);
