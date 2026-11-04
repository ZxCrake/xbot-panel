const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const H = { "User-Agent": UA };
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }

async function show(label, url, opts = {}) {
  const r = await fetch(url, { headers: { ...H, ...(opts.cookie !== false ? { cookie: jar.s } : {}) }, ...opts });
  const t = await r.text(); absorb(r);
  console.log("==", label, r.status, url.slice(0, 90));
  console.log("forms:", [...t.matchAll(/<form[^>]*>/g)].map((m) => m[0]).join(" ~ "));
  console.log("inputs:", [...t.matchAll(/<input[^>]*>/g)].map((m) => m[0].replace(/\s+/g, " ").slice(0, 150)).join("\n  "));
  return t;
}

await show("legacy ServiceLogin", "https://accounts.google.com/ServiceLogin?service=mail&nojs=1");
await show("v3 nojs", "https://accounts.google.com/v3/signin/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin");
await show("kailey", "https://accounts.google.com/ggprod/otherscript/identifier?nojs=1&flowName=GlifWebSignIn&flowEntry=ServiceLogin&service=mail");
