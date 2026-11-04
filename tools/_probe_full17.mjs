const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const r = await fetch("https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&emr=1&followup=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&osid=1&passive=1209600&service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin", { headers: { "User-Agent": UAS } });
const h = await r.text();
console.log("len", h.length);
console.log("iframes:", [...h.matchAll(/<iframe[^>]*>/g)].map((m) => m[0].slice(0, 260)).join("\n"));
console.log("6Lf:", (h.match(/6Lf[^"&\s<>]*/g) || []).slice(0, 5).join(","));
console.log("js_disabled:", (h.match(/js_disabled/g) || []).length);
