const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
function g(re, h) { return (re.exec(h) || [])[1] || ""; }
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }

const GETU = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin";
const r = await fetch(GETU, { headers: { "User-Agent": UAS } });
const html = await r.text(); absorb(r);
const sid = g(/"FdrFJe":"([^"]+)"/, html);
const at = g(/"SNlM0e":"([^"]+)"/, html) || g(/name="at"[^>]*value="([^"]+)"/, html);
const dsh = g(/"Qzxixc":"([^"]+)"/, html) || g(/name="usi"[^>]*value="([^"]+)"/, html);
const bl = g(/k=([\w.-]+)\.L\.B1\.O/, html);
const blFull = (html.match(/boq-identity\.[\w.-]+/g) || [])[0] || "";
console.log("sid:", sid, "at:", at.slice(0, 16) + "…", "dsh:", dsh.slice(0, 16), "bl:", bl, "|", blFull);

const url = `https://accounts.google.com/v3/signin/_/AccountsSignInUi/data/batchexecute?rpcids=NABu5d&source-path=%2Fv3%2Fsignin%2Fidentifier&f.sid=${sid}&bl=${encodeURIComponent(blFull || bl)}&hl=fr&_reqid=1&rt=c`;
async function tryFreq(label, freq) {
  const body = "f.req=" + encodeURIComponent(JSON.stringify([[["NABu5d", JSON.stringify(freq), null, "generic"]]])) + "&at=" + encodeURIComponent(at) + "&";
  const p = await fetch(url, { method: "POST", headers: { "User-Agent": UAS, "Content-Type": "application/x-www-form-urlencoded", cookie: jar.s }, body });
  const t = await p.text();
  console.log("\n[", label, "]", p.status, t.slice(0, 700).replace(/\n/g, " "));
}
const E = "xbot0y2u8155@gmail.com", P = "Xb-0y2u81-7139";
await tryFreq("1", [null, [["identifier", E], ["at", at]], 1]);
await tryFreq("2", [null, [["identifier", E]], "1", []]);
await tryFreq("3", [null, [["identifier", E], ["hiddenPassword", ""], ["usi", dsh], ["domain", ""], ["region", "FR"], ["bgresponse", ""], ["action", "1"], ["at", at]]]);
await tryFreq("4", [null, [["identifier", E]], null, null, null, null, 1]);
await tryFreq("5", ["", [null, [["identifier", E]], "1", null, []]]);
