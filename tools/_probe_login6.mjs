const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";

function jarFrom(r) {
  let jar = "";
  const list = r.headers.getSetCookie ? r.headers.getSetCookie() : [];
  for (const c of list) jar += (jar ? "; " : "") + c.split(";")[0];
  return jar;
}

// 1) GET page nojs, extraire tokens
const U = "https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const r = await fetch(U, { headers: { "User-Agent": UA } });
const html = await r.text();
const qz = (/\"Qzxixc\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
const sn = (/\"SNlM0e\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
console.log("Qzxixc:", qz.slice(0, 24), "SNlM0e:", sn.slice(0, 24));
const jar = jarFrom(r);
console.log("cookies:", jar.split(";").length);

// 2) POSTs candidats avec ct=SNlM0e, usi=Qzxixc
const body = new URLSearchParams({
  PageNum: "1",
  identifier: "xbot0sif9x@gmail.com",
  ct: sn,
  usi: qz,
  domain: "",
  region: "FR",
});
const endpoints = [
  "https://accounts.google.com/v3/signin/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin",
  "https://accounts.google.com/v3/signin/identifier",
  "https://accounts.google.com/signin/v2/identifier",
];
for (const e of endpoints) {
  try {
    const p = await fetch(e, {
      method: "POST",
      headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar },
      body,
    });
    const t = await p.text();
    console.log("POST", e.split("?")[0], "->", p.status, "|", t.slice(0, 160).replace(/\n/g, " "));
  } catch (err) {
    console.log("POST", e, "-> ERR", err.message);
  }
}
