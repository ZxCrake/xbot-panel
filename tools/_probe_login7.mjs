const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const U = "https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const r = await fetch(U, { headers: { "User-Agent": UA } });
const html = await r.text();
const qz = (/\"Qzxixc\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
const sn = (/\"SNlM0e\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
let jar = "";
for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar += (jar ? "; " : "") + c.split(";")[0];

const body = new URLSearchParams({ PageNum: "1", identifier: "xbot0sif9x@gmail.com", ct: sn, usi: qz, domain: "", region: "FR" });
const p = await fetch(U, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body });
const t = await p.text();
console.log("S1:", p.status);
console.log(t.slice(0, 1200).replace(/\n/g, " "));
