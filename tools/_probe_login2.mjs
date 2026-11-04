import("puppeteer").then(async ({ default: p }) => {
  const b = await p.launch({ headless: "new", ignoreDefaultArgs: ["--enable-automation"], args: ["--no-sandbox"] });
  const pg = await b.newPage();
  await pg.evaluateOnNewDocument(() => Object.defineProperty(navigator, "webdriver", { get: () => undefined }));
  await pg.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36");
  const S = (n) => new Promise((r) => setTimeout(r, n));
  const dump = async (l) => console.log(l, JSON.stringify(await pg.evaluate(() => ({
    url: location.href.split("?")[0],
    inputs: [...document.querySelectorAll("input")].map(e => e.id || e.name || e.type).slice(0, 6),
    t: document.body.innerText.replace(/\n+/g, " | ").slice(0, 160),
  }))));
  await pg.goto("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  await pg.type("#identifierId", "xbot0sif9x@gmail.com");
  await pg.click("#identifierNext").catch(async () => {
    await pg.evaluate(() => [...document.querySelectorAll("[role=button],button")].find(x => /Next|Suivant/i.test(x.innerText || ""))?.click());
  });
  await S(4000);
  await dump("APRES-ID");
  const next2 = await pg.evaluate(() => {
    const el = [...document.querySelectorAll("[role=button],button")].find(x => /Next|Suivant/i.test(x.innerText || ""));
    if (el) { el.click(); return "clicked:" + el.id; }
    return "none";
  });
  console.log("NEXT2", next2);
  await S(4000);
  await dump("APRES-2");
  await b.close();
}).catch(e => { console.error(e.message); process.exit(1); });
