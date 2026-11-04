const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const V3 = "https://accounts.google.com/v3/signin/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";

// 1) GET v3 lui-même : cookies + tokens de CETTE session
const r = await fetch(V3, { headers: { "User-Agent": UA } });
const html = await r.text();
console.log("v3 GET status:", r.status, "len:", html.length);
const usi = (/name="usi" value="([^"]+)"/.exec(html) || [])[1] || (/\"Qzxixc\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
const ct = (/\"SNlM0e\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
console.log("usi:", usi.slice(0, 20), "ct:", ct.slice(0, 20));
console.log("forms on v3:", (html.match(/<form/g) || []).length);
let jar = "";
for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar += (jar ? "; " : "") + c.split(";")[0];
console.log("cookies n°:", jar.split(";").filter(Boolean).length);

async function post(label, body) {
  const p = await fetch(V3, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body: new URLSearchParams(body) });
  const t = await p.text();
  const txt = t.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, "|").replace(/\|+/g, " | ").replace(/\s+/g, " ").trim();
  console.log(label, "->", p.status, "::", txt.slice(0, 300));
  return [p, t];
}

await post("at+identifier", { at: ct, identifier: "xbot0sif9x@gmail.com" });
await post("at+PageNum+identifier", { at: ct, PageNum: "1", identifier: "xbot0sif9x@gmail.com" });
await post("at+ct+usi+identifier", { at: ct, ct, usi, identifier: "xbot0sif9x@gmail.com" });
await post("nojs param only at", { at: ct, nojs: "1", identifier: "xbot0sif9x@gmail.com" });
