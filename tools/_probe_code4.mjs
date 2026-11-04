const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const H = { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded" };
const email = "xbot0uvl1d70@gmail.com";
function g(re, html) { return (re.exec(html) || [])[1] || ""; }

async function run(flowName) {
  const jar = { s: "" };
  const absorb = (r) => { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; };
  const r = await fetch(`https://accounts.google.com/v3/signin/identifier?service=mail&flowName=${flowName}&flowEntry=ServiceLogin`, { headers: H });
  const html = await r.text(); absorb(r);
  const usi = g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html);
  const at = g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html);
  const p = await fetch(`https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=${flowName}&service=mail`, { method: "POST", headers: { ...H, cookie: jar.s }, body: new URLSearchParams({ identifier: email, hiddenPassword: "", usi, domain: "", region: g(/name="region"[^>]*value="([^"]*)"/, html) || "FR", action: "1", at }) });
  const h = await p.text();
  console.log(flowName, "->", p.status, "url:", p.url.slice(0, 120));
  console.log(flowName, "inputs:", [...h.matchAll(/<input[^>]*>/g)].map((m) => `${g(/name="([^"]*)"/, m[0])}=${g(/value="([^"]*)"/, m[0]).slice(0, 20)}`).join(" ; ").slice(0, 300));
  console.log(flowName, "text:", h.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 250));
}
await run("GlifWebSignIn");
await run("WebLiteSignIn");
