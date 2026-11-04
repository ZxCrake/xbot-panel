const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const GET_U = "https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin";

function parse(html) {
  const g = (re) => (re.exec(html) || [])[1] || "";
  return {
    usi: g(/name="usi" value="([^"]+)"/),
    region: g(/name="region" value="([^"]*)"/),
    at: g(/name="at" value="([^"]+)"/) || g(/\"SNlM0e\":\"([^\"]+)\"/),
    bg: g(/name="bgresponse"[^>]*value="([^"]*)"/),
    idin: g(/name="identifierInput"[^>]*value="([^"]*)"/),
  };
}
function inputsOf(html) {
  return [...html.matchAll(/<input[^>]*>/g)].map((m) => {
    const n = (/name="([^"]*)"/.exec(m[0]) || [])[1];
    const v = (/value="([^"]*)"/.exec(m[0]) || [])[1] || "";
    return `${n}=${v.slice(0, 16)}`;
  }).join(" ; ");
}
function txt(html) {
  return html.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, "|").replace(/\|+/g, " ").replace(/\s+/g, " ").trim().slice(0, 220);
}

let jar = "";
let r = await fetch(GET_U, { headers: { "User-Agent": UA } });
let html = await r.text();
for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar += (jar ? "; " : "") + c.split(";")[0];
let t = parse(html);
const ACTION = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(t.usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;

async function post(label, bodyObj) {
  const p = await fetch(ACTION, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body: new URLSearchParams(bodyObj) });
  const tt = await p.text();
  for (const c of (p.headers.getSetCookie ? p.headers.getSetCookie() : [])) jar += "; " + c.split(";")[0];
  console.log(label, p.status, "::", txt(tt));
  console.log(label, "IN:", inputsOf(tt).slice(0, 400));
  return tt;
}

console.log("GET ok, usi:", t.usi.slice(0, 16), "at:", t.at.slice(0, 16), "bg:", t.bg.slice(0, 12));
let h2 = await post("S1", { identifier: "xbot0sif9x@gmail.com", hiddenPassword: "", usi: t.usi, domain: "", region: t.region, bgresponse: t.bg, action: "1", at: t.at });
let t2 = parse(h2);
let h3 = await post("S2", { identifier: "xbot0sif9x@gmail.com", hiddenPassword: "", usi: t2.usi || t.usi, domain: "", region: t2.region || t.region, action: "1", at: t2.at });
if (t2.idin) console.log("identifierInput:", t2.idin.slice(0, 40));
if (!/name="passwd"/.test(h3)) {
  const t3 = parse(h3);
  await post("S3", { identifier: "xbot0sif9x@gmail.com", hiddenPassword: "", usi: t3.usi || t.usi, domain: "", region: t3.region || t.region, action: "1", at: t3.at });
}
