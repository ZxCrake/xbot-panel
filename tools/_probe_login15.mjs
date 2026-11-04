const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const BASE = "https://accounts.google.com/v3/signin/identifier";

function toks(html) {
  return {
    usi: (/name="usi" value="([^"]+)"/.exec(html) || /\"Qzxixc\":\"([^\"]+)\"/.exec(html) || [])[1] || "",
    at: (/name="at" value="([^"]+)"/.exec(html) || /\"SNlM0e\":\"([^\"]+)\"/.exec(html) || [])[1] || "",
    dsh: (/name="dsh" value="([^"]+)"/.exec(html) || [])[1] || "",
    region: (/name="region" value="([^"]*)"/.exec(html) || [])[1] || "FR",
  };
}
function inputList(html) {
  return [...html.matchAll(/<input[^>]*>/g)].map((m) => {
    const n = (/name="([^"]*)"/.exec(m[0]) || [])[1];
    const v = (/value="([^"]*)"/.exec(m[0]) || [])[1];
    return `${n}=${(v || "").slice(0, 20)}`;
  });
}
function visible(html) {
  return html.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, "|").replace(/\|+/g, " | ").replace(/\s+/g, " ").trim().slice(0, 300);
}

let jar = "";
let r = await fetch(`${BASE}?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin`, { headers: { "User-Agent": UA } });
let html = await r.text();
for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar += (jar ? "; " : "") + c.split(";")[0];
let t = toks(html);
console.log("GET:", t.usi.slice(0, 18), t.at.slice(0, 18), "dsh:", t.dsh || "(none)");
console.log("inputs:", inputList(html).join(" ; ").slice(0, 300));

async function step(label, bodyObj) {
  const p = await fetch(`${BASE}?flowEntry=ServiceLogin&flowName=GlifWebSignIn&service=mail`, {
    method: "POST",
    headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar },
    body: new URLSearchParams(bodyObj),
  });
  const tt = await p.text();
  for (const c of (p.headers.getSetCookie ? p.headers.getSetCookie() : [])) jar += "; " + c.split(";")[0];
  console.log(label, p.status, "::", visible(tt));
  console.log(label, "inputs:", inputList(tt).join(" ; ").slice(0, 400));
  return tt;
}

let h2 = await step("S1", { identifier: "xbot0sif9x@gmail.com", hiddenPassword: "", usi: t.usi, domain: "", region: t.region, action: "1", at: t.at });
let t2 = toks(h2);
let h3 = await step("S2", { PageNum: "1", at: t2.at, identifier: "xbot0sif9x@gmail.com", action: "1", usi: t2.usi, region: t2.region });
if (!/name="passwd"/.test(h3)) {
  await step("S3", { at: toks(h3).at, identifier: "xbot0sif9x@gmail.com", action: "1", usi: toks(h3).usi, region: toks(h3).region });
}
