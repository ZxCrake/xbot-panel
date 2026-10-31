// tools/gmail_create.mjs — crée des comptes Gmail (Puppeteer + 2captcha) puis
// les écrit dans emails.txt pour l'action 14 « Change Email ».
//
// Usage :
//   node tools/gmail_create.mjs [nb] [cle2captcha] [chemin/emails.txt]
//     nb            : nombre de comptes à créer (défaut 1)
//     cle2captcha   : clé API 2captcha (défaut : env CAPTCHA_API_KEY)
//     emails.txt    : sortie (défaut : workspace/emails.txt ou DATA_ROOT users)
//
// Dépendance : npm i puppeteer   (2captcha via fetch natif, pas de lib)
// Une ligne par compte, format : adresse:mot_de_passe

import fs from "node:fs";
import puppeteer from "puppeteer";

const key = process.argv[3] || process.env.CAPTCHA_API_KEY || "";
const count = Math.max(1, Number(process.argv[2]) || 1);
const outFile = process.argv[4] || "workspace/emails.txt";
if (!key) { console.error("CAPTCHA_API_KEY manquant"); process.exit(1); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function solveCaptcha(imageB64) {
  const form = new URLSearchParams({ key, action: "in", json: "1", method: "12" });
  const sub = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: form })).json();
  if (sub.request === undefined) throw new Error("in.php: " + JSON.stringify(sub));
  const id = sub.request;
  for (let i = 0; i < 30; i++) {
    await sleep(2000);
    const q = await (await fetch(`https://2captcha.com/res.php?key=${key}&action=get&id=${id}&json=1`)).json();
    if (q.request && q.request !== "NOT_FOUND" && q.request !== "Z") return q.request;
  }
  throw new Error("captcha non résolu (timeout res.php)");
}

async function createAccount() {
  const browser = await puppeteer.launch({ headless: "new" });
  try {
    const page = await browser.newPage();
    await page.goto("https://accounts.google.com/signup", { waitUntil: "networkidle2" });

    const stamp = Date.now().toString(36).slice(-6);
    const emailPrefix = "xbot" + stamp;
    const password = `Xb-${stamp}-${Math.floor(Math.random() * 9000 + 1000)}`;

    // Étape 1 : prénom / nom / identifiant
    await page.waitForFunction(() => document.querySelector("#firstname, [name='firstname']"), { timeout: 15000 });
    if (await page.$("#firstname")) await page.type("#firstname", "Xbot");
    if (await page.$("#lastname")) await page.type("#lastname", stamp);
    await page.type(await page.$("#username") ? "#username" : "[name='identifier']", emailPrefix);
    await page.click("#next");
    await sleep(1200);

    // Étape 2 : mot de passe (+ confirmation si champ distinct)
    await page.waitForFunction(() => document.querySelector("#passwd, [name='passwd']"), { timeout: 15000 });
    await page.type(await page.$("#passwd") ? "#passwd" : "[name='passwd']", password);
    const conf = await page.$("[name='confirm-passwd']");
    if (conf) await page.type(conf, password);
    await page.click("#next");
    await sleep(1500);

    // Captcha (imageless Google = code 12 caractères) si présent
    await page.waitForFunction(() => document.querySelector("img[src^='data:image'], #captcha-image"),
      { timeout: 8000 }).catch(() => {});
    const b64 = await page.evaluate(() => {
      const img = document.querySelector("img[src^='data:image']") || document.querySelector("#captcha-image");
      return img ? img.src.split(",")[1] : "";
    });
    if (b64) {
      const code = await solveCaptcha(b64);
      const sel = await page.$("[name='captchaAnswer']") ? "[name='captchaAnswer']" : "#captchaimg";
      await page.type(sel, code, { delay: 40 });
    }
    const nextBtn = await page.$("#next");
    if (nextBtn) { await nextBtn.click(); await sleep(2500); }

    const full = await page.evaluate(() =>
      (document.body.innerText.match(/[\w.-]+@gmail\.com/) || [""])[0]);
    const email = full || `${emailPrefix}@gmail.com`;
    console.log(JSON.stringify({ email, password }));
    return `${email}:${password}`;
  } finally {
    await browser.close();
  }
}

const lines = [];
for (let i = 0; i < count; i++) {
  try { lines.push(await createAccount()); }
  catch (e) { console.error(`compte ${i + 1}: ${e.message}`); }
}
if (lines.length) {
  fs.mkdirSync((outFile.match(/^(.*)[/\\][^/\\]*$/) || ["", "."])[1] || ".", { recursive: true });
  const prev = fs.existsSync(outFile) ? fs.readFileSync(outFile, "utf-8") : "";
  const merged = [...prev.split("\n").filter(Boolean).slice(-50), ...lines].join("\n") + "\n";
  fs.writeFileSync(outFile, merged);
  console.log("écrit:", outFile, "→", lines.length, "ligne(s)");
}
