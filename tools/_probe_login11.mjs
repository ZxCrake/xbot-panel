const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const G = "https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const V3 = "https://accounts.google.com/v3/signin/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const r = await fetch(G, { headers: { "User-Agent": UA } });
const html = await r.text();
const usi = (/name="usi" value="([^"]+)"/.exec(html) || [])[1] || "";
const ct = (/\"SNlM0e\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
let jar = "";
for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar += (jar ? "; " : "") + c.split(";")[0];

async function post(label, url, body) {
  const p = await fetch(url, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body: new URLSearchParams(body) });
  const t = await p.text();
  const txt = t.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, "|").replace(/\|+/g, " | ").replace(/\s+/g, " ").trim();
  console.log(label, "->", p.status, "::", txt.slice(0, 700));
}

await post("at+ct+usi", V3, { at: ct, ct, usi, identifier: "xbot0sif9x@gmail.com" });
await post("at only", V3, { at: ct, identifier: "xbot0sif9x@gmail.com" });
await post("ct+usi no at", V3, { ct, usi, identifier: "xbot0sif9x@gmail.com" });
await post("full v2-style", V3, { PageNum: "1", at: ct, ct, usi, domain: "", region: "FR", hiddenPassword: "", ca: "", identifier: "xbot0sif9x@gmail.com" });
