// Login Gmail en HTML classique (fetch + hidden fields), sans JS.
const U = "https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";
const mail = "xbot0sif9x@gmail.com";
const pwd = "Xb-0sif9x-7777";

const parse = (html) => {
  const fields = {};
  for (const m of html.matchAll(/<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"/g)) fields[m[1]] = m[2];
  for (const m of html.matchAll(/<input[^>]*value="([^"]*)"[^>]*name="([^"]+)"/g)) fields[m[2]] = m[1];
  return fields;
};

let res = await fetch(U, { headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36" } });
let html = await res.text();
let jar = res.headers.get("set-cookie");
console.log("STEP1 fields:", Object.keys(parse(html)));

const f1 = parse(html);
const body1 = new URLSearchParams({ ...f1, PageNum: "1", identifier: mail });
res = await fetch("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36", cookie: jar || "" },
  body: body1,
});
html = await res.text();
const f2 = parse(html);
console.log("STEP2 url:", res.url || "?", "keys:", Object.keys(f2), "has-passwd:", /name="passwd"|id="passwd"/.test(html));
console.log("RAW2:", html.slice(0, 600).replace(/\n/g, " "));
jar = res.headers.get("set-cookie") || jar;

if (/name="passwd"/.test(html) || /id="passwd"/.test(html)) {
  const body2 = new URLSearchParams({ ...f2, PageNum: "2", Passwd: pwd });
  res = await fetch(res.url || U, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36", cookie: jar || "" }, body: body2 });
  html = await res.text();
  console.log("STEP3 len:", html.length, "code?:", (html.match(/\b\d{6}\b/) || [""])[0], "inbox?:", /Confirm your email|Gmail is|Inbox/.test(html));
}
