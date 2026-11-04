const UAS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const jar = { s: "" };
function absorb(r) { for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar.s += (jar.s ? "; " : "") + c.split(";")[0]; }
const H = { "User-Agent": UAS };
const urls = [
  "https://www.google.com/accounts/TListS?nojs=1",
  "https://www.google.com/a/service/identifier?nojs=1",
  "https://accounts.google.com/AccountChooser?nojs=1&service=mail",
  "https://mail.google.com/mail/ca/u/0/",
  "https://m.gmail.com/",
];
for (const u of urls) {
  try {
    const r = await fetch(u, { headers: { ...H, cookie: jar.s } });
    const t = await r.text();
    absorb(r);
    console.log("==", u, r.status, "len", t.length);
    console.log("  forms:", [...t.matchAll(/<form[^>]*>/g)].map((m) => m[0]).join(" ~ ").slice(0, 300));
    console.log("  inputs:", [...t.matchAll(/<input[^>]*>/g)].map((m) => m[0].replace(/\s+/g, " ").slice(0, 120)).slice(0, 8).join(" ;; ").slice(0, 400));
  } catch (e) { console.log("==", u, "ERR", e.message); }
}
