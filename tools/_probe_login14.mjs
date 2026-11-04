const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const GET_U = "https://accounts.google.com/v3/signin/identifier?dsh&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail";

const r = await fetch("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { headers: { "User-Agent": UA } });
const html = await r.text();
const usi = (/\"Qzxixc\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
const at = (/\"SNlM0e\":\"([^\"]+)\"/.exec(html) || [])[1] || "";
const region = (/name="region" value="([^"]*)"/.exec(html) || [])[1] || "FR";
let jar = "";
for (const c of (r.headers.getSetCookie ? r.headers.getSetCookie() : [])) jar += (jar ? "; " : "") + c.split(";")[0];
console.log("usi:", usi.slice(0, 18), "at:", at.slice(0, 18), "region:", region, "cookies:", jar.split(";").filter(Boolean).length);

const action = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
const body = new URLSearchParams({
  identifier: "xbot0sif9x@gmail.com",
  hiddenPassword: "",
  usi,
  domain: "",
  region,
  bgresponse: "!9Pel95PNAAY187QsFfNCuFu3sJZTOwU7AEABEArZ1KsoDl80edA0TQym8xNYVV6GrtWWMF5r8qi-JBIlsPTf7FnmXyCmeS--IGRZgaPYWaP-8FB3JdK_rlWVAgAAAbhSAAAAvGgBB34AT1O2yTSXDq-v98oYEHYbe2jB8Nw7xePjYleR-ClgrDD3g3biyRWl9mYBjUovgYwuCxDFUTUBkfvlg-lZEr0Yzw6tJiE9UUTQe363A6hrkHSZBWcsoGiG57sHi7tO7PMLGiGllB-Kz-xte4U6nV6fGUirQ2FlYgk_rWPvJiUUa4myblPGikOyjo8w979Mphg6M0JoQgddLTDsVcR5Ld8fnoXfeZkGRUDUEYZCp7Q6azAryqNC0mLazI34kYkBLZ6lJaMVzyMa5_ppJ2MEQguzEDnZkHk8sFKqNpLp7JN0B4BuWOQnVyzKXIweu5qYKns78xgaJ5zAV_2C5-n0O5DM54kccla7qoNjE8tvNx1SX22jiTiUV-WWtAyblFhYLPHTFqgNDyDplFIJUm_Sw3iGVuTl3CjolGobRU2l5_LizUs3tQa_LIa_N_DRqVzaEjCfTWQptam9xJ0kDn8bBuFLMOeTTJc8VR3XFzuPpfWmY16_HjpurckeX_k5LhGl8_qy-Er9kp9uQd1fyV9_XdNzDbaLsJMm52ViBxGmoTr_KUOTQ9bDQNT8XEIKBTEUQR-QgRpr9pgvSaGgDr9sVRISnHoX-Wjrm7qZ1np9U35hE4TT5z7tO6_OH413e513YQbDHbBT6L89oYrgInQsxOBjSP6QNVxTX-4oXYB_X7jEBVIB6vQ2-h8xvLRu5Px6oS091B4ZyU-GYjwkZn1DrfG_HTcb4ajH-co6pwhZnWaGwPxem1bKeL0jP9bf0CetPLBSCChsMD3EHDoKlO5bJMqI8-u5MxpDujM4SUMzwJ78lcUCvNmTh941C9RwN_3YpXonLY1pFsNPR3drDboWYlBasPsZB-N3xcH95uOvNHtInYWLooNXHsmnXKamd9fWq9x818v-gREEtL8_ZeFfMiu9K2w-L8H9jevZcaHL1kCcumjRtNxE7EZ2oh63BTKYkOB3ClKVAYMweri57F-GD2Wfv-UCvNblpU7qBawUrM0D8zKxHwWD_DCzrTt8rdMrYF0tX_NhybQcbfEtdvuuc8kvE4WgF4Drb6Lc5p7Ac7qxAauPVXDYZbzbUZ3PFC7JRP_sVBpb5UTW54nQVFvfjwtWsO7zc4Q8ns9WDeFV0ntCVfriq6EJt1tguoANZ34NI1PioQPlXh1n08UVZCHdrGAHppa6jqcSKoXN7r3oZ3OlW5u8NfKm-uYQDwQTHfRWQsy45d8Y80RV8JjZnuBdxVCC7HIEoQSUCLNGoQHFvJMmjAFfNnhdLPXSfL5DuUS8-GYtpAkt4TikWEScTUzlFzfiK3MuyeSxJVPMEV3O8Tpa-g0QBYWDoy_UDc_yzOUOOswJIjhoiH3nWjEllRy99IMoG_-Cpw_qIqgnp7wg-RKZ8CUd4sbkr_lKvODVC7zE0woioNUGVB0shXKMoEtOk5yyKA3HSJ6PHphrBH6CCfVooHZEwv25yRVhuhPXhD3A78nsyh0zXrtZDBudwGOvuh8wSRAKKoOC3oUOWFbNILgmL8lwufLHuog6bPb5Epcn11XzhmI6qBggkeoZR8turuIRfb5URdDBaOQp6GhXH_U6Qnk-gRNl5NcMCdvDSJO8w1SyffqV8diKLLa6IskgZuKgdkOQZ-9ebTp513tqhMci_wfwPQ3LnEYi5pF3Lprl6I1SBYEb-RFoS9nhsHzj82pBRGRRlJWJ4NL23mrQ9V_bKv8vN1Azbk4laNTqfg8BwaKrWoaqL3ovqFJmYK8NPq_s24S8romkiGZnOOussPH62zZdjxG2oSOtZe41o3FAnln_w9k4S6b3UGk4oiHj6N1ZAcdjTCxPFDiZFt2ctRK5jmEZ2MVVPPOYYEYMaxseSarXWaenj_UsE4FVL_JWqAgLp4unJLzRs5SrcsQggcy3K2rYo85Y1fJSEW6VNi-geOuc3-MZyRrgvDaPyGnS3L4-I9fVOC2I81q0Mt8",
  action: "1",
  at,
});
const p = await fetch(action, { method: "POST", headers: { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded", cookie: jar }, body });
const t = await p.text();
let jar2 = jar;
for (const c of (p.headers.getSetCookie ? p.headers.getSetCookie() : [])) jar2 += "; " + c.split(";")[0];
const txt = t.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "").replace(/<[^>]+>/g, "|").replace(/\|+/g, " | ").replace(/\s+/g, " ").trim();
console.log("STEP1:", p.status, "::", txt.slice(0, 400));

// Étape 2 si form passwd présent : nommer les inputs du POST suivant
const inputs2 = [...t.matchAll(/<input[^>]*>/g)].map((m) => m[0].slice(0, 120));
console.log("INPUTS2:", JSON.stringify(inputs2.slice(0, 12), null, 0));
