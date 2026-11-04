const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const U = "https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const r = await fetch(U, { headers: { "User-Agent": UA } });
const html = await r.text();
const qz = (/\"Qzxixc\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
const sn = (/\"SNlM0e\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
let jar = "";
for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar += (jar ? "; " : "") + c.split(";")[0];

function explain(t) {
  const ps = [...t.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g)].map((m) => m[1].trim());
  return ps.join(" | ").slice(0, 500) || t.replace(/<[^>]+>/g, " ").slice(0, 500);
}

const tries = [
  { name: "v2 full + nojs, ct/usi", body: new URLSearchParams({ PageNum: "1", identifier: "xbot0sif9x@gmail.com", ct: sn, usi: qz, domain: "", region: "FR" }) },
  { name: "v2 nojs, only identifier", body: new URLSearchParams({ identifier: "xbot0sif9x@gmail.com" }) },
  { name: "v3 full + nojs, ct/usi/at", body: new URLSearchParams({ PageNum: "1", at: sn, identifier: "xbot0sif9x@gmail.com", ct: sn, usi: qz }) },
];
for (const urlName of ["https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", "https://accounts.google.com/v3/signin/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin"]) {
  for (const t of tries) {
    const p = await fetch(urlName, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body: t.body });
    const b = await p.text();
    console.log(urlName.split("?")[0], "|", t.name, "->", p.status, "::", explain(b));
  }
}
