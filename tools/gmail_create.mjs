// tools/gmail_create.mjs — comptes Gmail (Puppeteer + 2captcha) pour l'action 14.
//
// Modes :
//   node tools/gmail_create.mjs create [nb] [cle2captcha] [chemin/emails.txt]
//       → crée `nb` comptes Gmail, ajoute « adresse:mot_de_passe » à emails.txt,
//         garde un index des profils (réutilisable pour lire la boîte plus tard).
//   node tools/gmail_create.mjs code <adresse> <mot_de_passe>
//       → lit la boîte et imprime le dernier code de vérification à 6 chiffres.
//
// Sélecteurs Google validés par sondage (nov. 2026) :
//   - signup/name : #firstName, #lastName ; bouton <button> « Suivant ».
//   - signup/birthdaygender : #day, #year ; mois = input sans id (jsname YPqjbf),
//     click()+focus() puis li[role=option] /^janvier$/i ; genre = li « Homme » ;
//     « Suivant », parfois 2e clic si #emailPhone absent.
//   - signup/collectemailphone : #emailPhone avec le suffixe @gmail.com ;
//     reCAPTCHA enterprise (sitekey 6Lf-_ekqAAAA…) résolu par 2captcha (enterprise=1).
//   - signup/verifyemail : input[name=code] (6 chiffres envoyés par e-mail).
//   - Le POST no-js pur (fetch seul) est rejeté : rrk=46 (bgresponse vide) ou
//     rrk=47 (bgresponse="js_disabled"). La lecture du code utilise donc les
//     pages RENDUES par JS dans le même navigateur (inputs bgresponse/at remplis).
//   - Les comptes en attente de validation ne sont PAS résolvables (idnf).
//
// Dépendance : npm i puppeteer

import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer";

const API = "https://2captcha.com";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";
const first = process.argv[2] || "create";
const BASE = first === "create" || first === "code" ? 3 : 2;
const MODE = first === "code" ? "code" : "create";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ── 2captcha ──────────────────────────────────────────────────────────────────

async function inPost(key, params) {
  const form = new URLSearchParams({ key, json: "1", ...params });
  const res = await fetch(`${API}/in.php`, { method: "POST", body: form });
  const data = await res.json();
  if (!data || data.status !== 1 || data.request === undefined) {
    throw new Error(`in.php: ${JSON.stringify(data)}`);
  }
  return String(data.request);
}

async function waitResult(key, id) {
  for (let i = 0; i < 40; i++) {
    await sleep(2500);
    const res = await fetch(
      `${API}/res.php?key=${encodeURIComponent(key)}&action=get&id=${id}&json=1`);
    const data = await res.json();
    if (data && data.status === 1 && data.request && data.request !== "NOT_FOUND") {
      return String(data.request);
    }
  }
  throw new Error("captcha non résolu (timeout res.php)");
}

async function solveImage(key, src) {
  const b64 = src.includes(",") ? src.split(",")[1] : src;
  return waitResult(key, await inPost(key, { method: "base64", body: b64 }));
}

async function solveRecaptcha(key, sitekey, pageurl) {
  return waitResult(key, await inPost(key, {
    method: "userrecaptcha", googlekey: sitekey, pageurl, enterprise: "1",
  }));
}

// ── Helpers Puppeteer ─────────────────────────────────────────────────────────

async function typeFirst(page, selectors, value) {
  for (const sel of selectors) {
    const el = await page.$(sel);
    if (el) { await el.type(value, { delay: 30 }); return true; }
  }
  return false;
}

async function clickNext(page) {
  await page.evaluate(() => {
    const b = [...document.querySelectorAll("button")].find(
      (x) => /^(suivant|next)$/i.test((x.textContent || "").trim()));
    if (b) b.click();
  });
  await sleep(1500);
}

async function solveCaptchaOnPage(page, key) {
  const info = await page.evaluate(() => {
    const out = { recaptcha: "", images: [] };
    for (const fr of document.querySelectorAll("iframe")) {
      const m = (fr.getAttribute("src") || "").match(/[?&]k=([-\w]+)/);
      if (m && !out.recaptcha) out.recaptcha = m[1];
    }
    document.querySelectorAll("img[src^='data:image']").forEach((i) => out.images.push(i.src));
    return out;
  });
  if (info.recaptcha) {
    const token = await solveRecaptcha(key, info.recaptcha, page.url());
    await page.evaluate((t) => {
      for (const ta of document.querySelectorAll("#g-recaptcha-response, [name='g-recaptcha-response']")) {
        ta.value = t;
      }
      const inner = document.querySelector("iframe")?.contentDocument;
      const ita = inner && inner.getElementById("g-recaptcha-response");
      if (ita) ita.value = t;
    }, token);
    return;
  }
  let n = 0;
  for (const src of info.images) {
    const answer = await solveImage(key, src);
    const input = await page.$(`[name='f-input-${n}']`) || await page.$("#captchaimg");
    if (input) await input.type(answer, { delay: 30 });
    n++;
  }
}

// ── Lecture de la boîte : chaîne nojs dans le MÊME navigateur (jeton `at` de la
//    page rendue, jar partagé). Le POST no-js pur (fetch seul) est rejeté
//    (rrk 46/47) car le vrai token d'ancre n'existe qu'avec JS activé. ────────

function g(re, h) { return (re.exec(h) || [])[1] || ""; }

function toks(html) {
  return {
    usi: g(/name="usi"[^>]*value="([^"]+)"/, html) || g(/"Qzxixc":"([^"]+)"/, html),
    at: g(/name="at"[^>]*value="([^"]+)"/, html) || g(/"SNlM0e":"([^"]+)"/, html),
    bg: g(/name="bgresponse"[^>]*value="([^"]*)"/, html),
    region: g(/name="region"[^>]*value="([^"]*)"/, html) || "FR",
  };
}

async function readCodeInBrowser(browser, email, password) {
  const p = await browser.newPage();
  try {
    await p.setUserAgent(UA);
    await p.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
    await p.goto("https://accounts.google.com/v3/signin/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
    await p.waitForSelector("#identifierId", { timeout: 15000 });
    await p.type("#identifierId", email, { delay: 20 });
    await p.evaluate(() => document.querySelector("#identifierNext")?.click());
    await sleep(1200);

    const html1 = await p.content();
    const t1 = toks(html1);
    const ck = await browser.cookies();
    const jarS = ck.map((c) => `${c.name}=${c.value}`).join("; ");
    const act = `https://accounts.google.com/v3/signin/identifier?dsh=${encodeURIComponent(t1.usi)}&flowEntry=ServiceLogin&flowName=WebLiteSignIn&service=mail`;
    const H = { "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded" };
    const p1 = await fetch(act, { method: "POST", headers: { ...H, cookie: jarS }, body: new URLSearchParams({ identifier: email, hiddenPassword: "", usi: t1.usi, domain: "", region: t1.region || "FR", bgresponse: t1.bg || "js_disabled", action: "1", at: t1.at }) });
    let h1 = await p1.text();
    if (!/name="passwd"/.test(h1)) return "";
    const t2 = toks(h1);
    const p2 = await fetch(act, { method: "POST", headers: { ...H, cookie: jarS }, body: new URLSearchParams({ PageNum: "2", passwd: password, at: t2.at, usi: t2.usi || t1.usi, domain: "", region: t2.region || t1.region || "FR", bgresponse: t2.bg || "js_disabled", action: "2" }) });
    const h2 = await p2.text();
    const body = h2.replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
    const cm = body.match(/\b(\d{6})\b/);
    if (cm) return cm[1];
    const mu = /https:\/\/mail\.google\.com[^"'<> ]*/.exec(h2);
    if (mu) {
      const p3 = await fetch(mu[0].replace(/&amp;/g, "&"), { headers: { "User-Agent": UA, cookie: jarS } });
      const h3 = (await p3.text()).replace(/<style[\s\S]*?<\/style>/g, "").replace(/<script[\s\S]*?<\/script>/g, "");
      const m3 = h3.match(/\b(\d{6})\b/);
      if (m3) return m3[1];
    }
    return "";
  } finally {
    await p.close();
  }
}

// ── Mode create ───────────────────────────────────────────────────────────────

async function createAccount(key, profilesDir) {
  const profileDir = path.join(profilesDir, `p${Date.now().toString(36)}`);
  fs.mkdirSync(profileDir, { recursive: true });
  const browser = await puppeteer.launch({
    headless: "new",
    userDataDir: profileDir,
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"],
  });
  try {
    const page = await browser.newPage();
    await page.setUserAgent(UA);
    await page.evaluateOnNewDocument(() => { Object.defineProperty(navigator, "webdriver", { get: () => undefined }); });
    await page.goto("https://accounts.google.com/signup", { waitUntil: "networkidle2" });

    const stamp = Date.now().toString(36).slice(-6);
    const prefix = "xbot" + stamp + Math.floor(Math.random() * 90);
    const email = `${prefix}@gmail.com`;
    const password = `Xb-${stamp}-${Math.floor(Math.random() * 9000 + 1000)}`;

    // Étape 1 — signup/name
    await page.waitForSelector("#firstName", { timeout: 20000 });
    await page.type("#firstName", "Xbot", { delay: 30 });
    await typeFirst(page, ["#lastName"], stamp);
    await clickNext(page);

    // Étape 2 — signup/birthdaygender
    await page.waitForSelector("#day", { timeout: 20000 });
    await page.type("#day", "15", { delay: 30 });
    await page.type("#year", "1990", { delay: 30 });
    await page.evaluate(() => {
      const month = [...document.querySelectorAll("input")].find(
        (i) => !i.id && i.getAttribute("jsname") === "YPqjbf");
      if (month) { month.click(); month.focus(); }
    });
    await sleep(600);
    await page.evaluate(() => {
      const opt = [...document.querySelectorAll("li[role=option]")].find(
        (li) => /^janvier$/i.test((li.textContent || "").trim()));
      if (opt) opt.click();
    });
    await sleep(400);
    await page.evaluate(() => {
      const el = [...document.querySelectorAll("li,option")].find(
        (x) => /^(homme|male)$/i.test((x.textContent || "").trim()));
      if (el) el.click();
    });
    await sleep(400);
    await clickNext(page);
    if (!(await page.$("#emailPhone"))) await clickNext(page);

    // Étape 3 — signup/collectemailphone
    await page.waitForSelector("#emailPhone", { timeout: 20000 });
    await page.type("#emailPhone", email, { delay: 30 });
    await typeFirst(page, ["#passwd", "[name='passwd']"], password);
    await solveCaptchaOnPage(page, key);
    await clickNext(page);

    // Étape 4 — signup/verifyemail : code lu dans le même navigateur
    await page.waitForSelector("[name='code']", { timeout: 30000 });
    let code = "";
    for (let i = 0; i < 15 && !code; i++) {
      code = await readCodeInBrowser(browser, email, password);
      if (!code) await sleep(2000);
    }
    if (!code) throw new Error("code 6 chiffres non trouvé dans la boîte");
    await (await page.$("[name='code']")).type(code, { delay: 30 });
    await clickNext(page);

    // Écran final — lire l'adresse confirmée
    let finalEmail = "";
    for (let i = 0; i < 20 && !finalEmail; i++) {
      await sleep(700);
      finalEmail = await page.evaluate(() =>
        (document.body.innerText.match(/[\w.-]+@gmail\.com/) || [""])[0]);
    }
    if (!finalEmail) throw new Error("adresse non confirmée à l'écran final");
    return { email: finalEmail, password, profileDir };
  } finally {
    await browser.close();
  }
}

async function runCreate() {
  const count = Math.max(1, Number(process.argv[BASE]) || 1);
  const key = process.argv[BASE + 1] || process.env.CAPTCHA_API_KEY || "";
  const outFile = process.argv[BASE + 2] || "workspace/emails.txt";
  if (!key) { console.error("CAPTCHA_API_KEY manquant"); process.exit(1); }
  const profilesDir = path.join(path.dirname(outFile), "gmail-profiles");
  fs.mkdirSync(profilesDir, { recursive: true });
  const indexFile = path.join(profilesDir, "index.json");
  const index = fs.existsSync(indexFile)
    ? JSON.parse(fs.readFileSync(indexFile, "utf-8")) : {};

  const lines = [];
  for (let i = 0; i < count; i++) {
    try {
      const acc = await createAccount(key, profilesDir);
      index[acc.email] = { dir: acc.profileDir, password: acc.password };
      lines.push(`${acc.email}:${acc.password}`);
      console.log(JSON.stringify(acc));
    } catch (e) {
      console.error(`compte ${i + 1}: ${e.message}`);
    }
  }
  if (lines.length) {
    fs.writeFileSync(indexFile, JSON.stringify(index, null, 1));
    const prev = fs.existsSync(outFile) ? fs.readFileSync(outFile, "utf-8") : "";
    const merged = [...prev.split("\n").filter(Boolean).slice(-50), ...lines].join("\n") + "\n";
    fs.writeFileSync(outFile, merged);
    console.log("écrit:", outFile, "→", lines.length, "ligne(s)");
  }
}

// ── Mode code (lecture dans un navigateur puppeteer) ──────────────────────────

async function runCode() {
  const email = process.argv[BASE];
  const password = process.argv[BASE + 1];
  if (!email || !password) { console.error("usage: … code <email> <mdp>"); process.exit(1); }
  const browser = await puppeteer.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"],
  });
  try {
    for (let i = 0; i < 10; i++) {
      const code = await readCodeInBrowser(browser, email, password);
      if (code) { console.log(code); return; }
      await sleep(2000);
    }
    console.error("pas de code 6 chiffres dans la boîte");
    process.exit(1);
  } finally {
    await browser.close();
  }
}

// ── Entrée ────────────────────────────────────────────────────────────────────

if (MODE === "code") { await runCode(); } else { await runCreate(); }
