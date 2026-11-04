// Mini-probe : quelles URLs de login Google passent en headless.
import("puppeteer").then(async ({ default: p }) => {
  const b = await p.launch({ headless: "new", ignoreDefaultArgs: ["--enable-automation"], args: ["--no-sandbox"] });
  const pg = await b.newPage();
  await pg.evaluateOnNewDocument(() => Object.defineProperty(navigator, "webdriver", { get: () => undefined }));
  console.log("UA:", await pg.evaluate(() => navigator.userAgent));
  const urls = [
    "https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin",
    "https://accounts.google.com/signin/v2/identifier?service=mail&flowName=WebLiteSignIn&flowEntry=ServiceLogin",
    "https://mail.google.com/mail/",
  ];
  for (const u of urls) {
    try {
      await pg.goto(u, { waitUntil: "networkidle2" });
      const st = await pg.evaluate(() => ({
        url: location.href.split("?")[0],
        inputs: [...document.querySelectorAll("input")].map(e => e.id || e.name || e.type).slice(0, 6),
        t: document.body.innerText.replace(/\n+/g, " | ").slice(0, 140),
      }));
      console.log(u.slice(30, 80), "→", JSON.stringify(st));
    } catch (e) { console.log(u, "ERR", e.message); }
  }
  await b.close();
}).catch(e => { console.error(e.message); process.exit(1); });
