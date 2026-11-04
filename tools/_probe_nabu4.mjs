const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
const GETU = "https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin";
const r = await fetch(GETU, { headers: { "User-Agent": UAS } });
const html = await r.text(); absorb(r);
const i = html.indexOf("SNlM0e");
console.log("SNlM0e ctx:", html.slice(i - 4, i + 80));
const j = html.indexOf("Qzxixc");
console.log("Qzxixc ctx:", html.slice(j - 4, j + 80));
const k = html.indexOf("FdrFJe");
console.log("FdrFJe ctx:", html.slice(k - 4, k + 60));
const l = html.indexOf("f.sid");
console.log("f.sid ctx:", html.slice(l - 4, l + 60));
// les inputs nommés avec valeur
const m = html.match(/<input[^>]*name="at"[^>]*>/) || [];
console.log("input at:", (m[0] || "").slice(0, 160));
