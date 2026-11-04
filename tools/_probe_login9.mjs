const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const U = "https://accounts.google.com/signin/v2/identifier?nojs=1&service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const r = await fetch(U, { headers: { "User-Agent": UA } });
const html = await r.text();
for (const m of html.matchAll(/<input[^>]*>/g)) console.log(m[0]);
console.log("--- jsname at:", (/.{0,80}jsname="at".{0,120}/s.exec(html) || ["none"])[0]);
console.log("--- button:", [...html.matchAll(/<(button|div)[^>]*jsname="(NwH2yd|k8eNnc)"[^>]*>/g)].map((m) => m[0]).join("\n"));
