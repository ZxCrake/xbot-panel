// Probe du flux signup Google : ordre réel des étapes + lecture du code.
const K = "b1147a35362c7fb3aca8c2e2630c412e";
import("puppeteer").then(async ({ default: p }) => {
  const b = await p.launch({ headless: "new", ignoreDefaultArgs: ["--enable-automation"],
                             args: ["--no-sandbox"] });
  const pg = await b.newPage();
  await pg.evaluateOnNewDocument(() => Object.defineProperty(navigator, "webdriver", { get: () => undefined }));
  const S = (n) => new Promise((r) => setTimeout(r, n));
  const step = () => pg.evaluate(() => (location.href.split("/steps/")[1] || location.href).split("?")[0]);
  const dump = async (l) => {
    const st = await pg.evaluate(() => ({
      u: (location.href.split("/steps/")[1] || "").split("?")[0],
      inputs: [...document.querySelectorAll("input")].map((e) => e.id || e.name || "?"),
      t: document.body.innerText.replace(/\n+/g, " | ").slice(0, 180),
    }));
    console.log(l, JSON.stringify(st));
  };
  const next = async () => {
    await pg.evaluate(() =>
      [...document.querySelectorAll("button")].find((x) => /Suivant|Next/i.test(x.innerText))?.click());
    await S(2500);
  };
  const choose = (re) => pg.evaluate((r) => {
    const els = [...document.querySelectorAll("li,[role=option]")];
    const el = els.find((e) => new RegExp("^(" + r + ")$", "i").test((e.innerText || "").trim()));
    if (el) { el.click(); return true; }
    return false;
  }, re);

  await pg.goto("https://accounts.google.com/signup", { waitUntil: "networkidle2" });
  await pg.type("#firstName", "Xbot");
  await pg.type("#lastName", "tst1");
  await next();
  await pg.waitForSelector("#day");
  await pg.type("#day", "1");
  await pg.type("#year", "1990");
  await pg.evaluate(() => {
    const m = [...document.querySelectorAll("input")].find((i) => !i.id);
    m.click(); m.focus();
  });
  await S(700);
  await choose("janvier|février|mars");
  await S(700);
  await choose("homme|male");
  await next();
  if (!(await pg.$("#emailPhone"))) await next();
  await dump("STEP3");
  const stamp = Date.now().toString(36).slice(-6);
  const pwd = `Xb-${stamp}-7777`;
  const mail = "xbot" + stamp;
  await pg.waitForSelector("#emailPhone");
  await pg.type("#emailPhone", mail + "@gmail.com");
  await next();
  await dump("STEP4");
  // Étape password si présente
  if (await pg.$("#passwd")) {
    await pg.type("#passwd", pwd);
    const conf = await pg.$("#confirm-passwd, [name='confirm-passwd']");
    if (conf) await conf.type(pwd);
    await next();
    await dump("STEP5");
  }
  // reCAPTCHA enterprise éventuel
  const sk = await pg.evaluate(() => {
    const f = [...document.querySelectorAll("iframe")].map((x) => x.src).find((s) => /recaptcha/.test(s));
    return f ? (f.match(/[?&]k=([-\w]+)/) || [])[1] : "";
  });
  console.log("SITEKEY", sk);
  if (sk) {
    const form = new URLSearchParams({ key: K, json: "1", method: "userrecaptcha", googlekey: sk, pageurl: pg.url(), enterprise: "1" });
    const sub = await (await fetch("https://2captcha.com/in.php", { method: "POST", body: form })).json();
    console.log("SUBMIT", JSON.stringify(sub));
    let token = "";
    for (let i = 0; i < 40; i++) {
      await S(2500);
      const q = await (await fetch(`https://2captcha.com/res.php?key=${K}&action=get&id=${sub.request}&json=1`)).json();
      if (q.status === 1 && q.request) { token = q.request; break; }
    }
    console.log("TOKEN len", token.length);
    await pg.evaluate((t) => {
      for (const e of document.querySelectorAll("#g-recaptcha-response, textarea[name='g-recaptcha-response']")) e.value = t;
      for (const f of document.querySelectorAll("iframe")) {
        try { const it = f.contentDocument && f.contentDocument.getElementById("g-recaptcha-response"); if (it) it.value = t; } catch (e) {}
      }
    }, token);
    await next();
    await dump("STEP6");
  }
  // Code de vérification : lire la boîte dans un 2e onglet (même session)
  const u = await step();
  if (/verifyemail/.test(u)) {
    const box = await b.newPage();
    await box.evaluateOnNewDocument(() => Object.defineProperty(navigator, "webdriver", { get: () => undefined }));
    await box.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36");
    await box.goto("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin&ifm=1",
                   { waitUntil: "networkidle2" });
    await S(2000);
    if (await box.$("#identifierId")) {
      await box.type("#identifierId", mail + "@gmail.com");
      await box.keyboard.press("Enter");
      await S(2500);
      console.log("BOX2", await box.evaluate(() => ({u: location.href.split("?")[0], i: [...document.querySelectorAll("input")].map(e => e.id || e.name || e.type).slice(0,8), t: document.body.innerText.replace(/\n+/g," | ").slice(0,160)})));
      const p2 = await box.evaluate(() => {
        for (const s of ["input[name='passwd']", "#passwd", "#pass", "[type='password']"])
          if (document.querySelector(s)) return s;
        return "";
      });
      console.log("PSEL", p2 || "aucun");
      if (p2) { await box.type(p2, pwd); await box.keyboard.press("Enter"); }
      await S(3500);
    }
    let code = "";
    for (let i = 0; i < 20 && !code; i++) {
      await S(1500);
      code = await box.evaluate(() => {
        const m = (document.body.innerText.match(/\b\d{4,8}\b/g) || []);
        return m[0] || "";
      });
    }
    console.log("CODE-LU", code);
    await box.close();
    if (code) {
      await pg.type("input[name='code'], #code", code, { delay: 40 });
      await next();
      await dump("FINAL");
      const em = await pg.evaluate(() => (document.body.innerText.match(/[\w.-]+@gmail\.com/) || [""])[0]);
      console.log("EMAIL", em, "PWD", pwd);
    }
  } else {
    const em = await pg.evaluate(() => (document.body.innerText.match(/[\w.-]+@gmail\.com/) || [""])[0]);
    console.log("EMAIL", em, "PWD", pwd);
  }
  await b.close();
}).catch((e) => { console.error("ERR", e.message); process.exit(1); });
