const U = "https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const r = await fetch(U, { headers: { "User-Agent": UA } });
const html = await r.text();
const forms = [...html.matchAll(/<form[^>]*>/g)].map(m => m[0]);
console.log("FORMS:", JSON.stringify(forms));
const inputs = [...html.matchAll(/<input[^>]*>/g)].map(m => m[0].slice(0, 140));
console.log("INPUTS:", JSON.stringify(inputs.slice(0, 12), null, 0));
console.log("COOKIES:", (r.headers.getSetCookie ? r.headers.getSetCookie().length : 0), "present");
let jar = "";
for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [r.headers.get("set-cookie")].filter(Boolean))) {
  jar += (jar ? "; " : "") + c.split(";")[0];
}
const body = new URLSearchParams();
for (const m of inputs) {
  const n = (/name="?([\w]+)"?/.exec(m) || [])[1];
  const v = (/value="?([^">]*)"?/.exec(m) || [])[1] ?? "";
  if (n) body.set(n, v);
}
body.set("identifier", "xbot0sif9x@gmail.com");
body.set("PageNum", "1");
const action = forms[0] ? (/action="?([^"> ]+)/.exec(forms[0]) || [])[1] : U;
console.log("ACTION:", action);
const r2 = await fetch(action, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body });
const h2 = await r2.text();
console.log("S2:", r2.status, h2.slice(0, 300).replace(/\n/g, " "));
