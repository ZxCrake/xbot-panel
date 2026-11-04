const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const G = "https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const r = await fetch(G, { headers: { "User-Agent": UA } });
const html = await r.text();
const usiHtml = (/name="usi" value="([^"]+)"/.exec(html) || [])[1] || "";
const qz = (/\"Qzxixc\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
const sn = (/\"SNlM0e\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
let jar = "";
for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar += (jar ? "; " : "") + c.split(";")[0];
console.log("usi(html)==usi(Qzxixc)?", usiHtml === qz, "| ct:", sn.slice(0, 12) + "…");

async function post(label, url, body) {
  const p = await fetch(url, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body });
  const t = await p.text();
  const ps = [...t.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).join(" | ");
  console.log(label, "->", p.status, "::", (ps || t.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").slice(0, 200)));
  return t;
}

const full = { PageNum: "1", hiddenPassword: "", ca: "", ct: sn, usi: usiHtml, domain: "", region: "FR", identifier: "xbot0sif9x@gmail.com" };
await post("v3?nojs full", G.replace("/v2/", "/v3/"), new URLSearchParams(full));
await post("v3 noq full", "https://accounts.google.com/v3/signin/identifier", new URLSearchParams(full));
await post("v3?nojs minus-page", G.replace("/v2/", "/v3/"), new URLSearchParams({ ...full, PageNum: undefined }));
