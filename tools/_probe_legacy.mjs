const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const urls = [
  "https://www.google.com/s2/accounts?service=mail&nojs=1",
  "https://www.google.com/accounts/ServiceLogin?service=mail&nojs=1",
  "https://mail.google.com/mail/u/0/?ui=1&nojs=1",
  "https://mail.google.com/mail/feed/atom/",
];
for (const u of urls) {
  try {
    const r = await fetch(u, { headers: { "User-Agent": UA } });
    const t = await r.text();
    console.log("==", u, r.status, "len", t.length);
    console.log("forms:", [...t.matchAll(/<form[^>]*>/g)].map((m) => m[0]).join(" ~ ").slice(0, 400));
    console.log("inputs:", [...t.matchAll(/<input[^>]*>/g)].map((m) => m[0].replace(/\s+/g, " ").slice(0, 130)).slice(0, 10).join("\n  "));
    const txt = t.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 200);
    console.log("txt:", txt);
  } catch (e) { console.log("==", u, "ERR", e.message); }
}
