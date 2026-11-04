import puppeteer from "puppeteer";

const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"] });
try {
  const page = await browser.newPage();
  const reqs = [];
  page.on("request", (rq) => {
    if (rq.method() === "POST") reqs.push({ url: rq.url(), body: rq.postData(), headers: rq.headers()["content-type"] || "" });
  });
  page.on("response", async (rs) => {
    for (const q of reqs) {
      if (q.url === rs.url() && q.resp === undefined) {
        try { q.resp = (await rs.text()).slice(0, 400); } catch { q.resp = "(no body)"; }
      }
    }
  });

  await page.goto("https://accounts.google.com/signin/v2/identifier?service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin", { waitUntil: "networkidle2" });
  console.log("inputs:", await page.evaluate(() => [...document.querySelectorAll("input")].map((i) => `${i.name || i.id || "?"}`).join(",")));

  const el = await page.$("#identifierId");
  await el.type("xbot0sif9x@gmail.com", { delay: 30 });
  await page.evaluate(() => document.querySelector("#identifierNext").click());
  await new Promise((r) => setTimeout(r, 4000));

  console.log("URL:", page.url());
  console.log("POSTS:", JSON.stringify(reqs, null, 1));
  console.log("state:", await page.evaluate(() => ({
    passwd: !!document.querySelector("[name='passwd']"),
    next2: !!document.querySelector("#passwordNext"),
    body: document.body.innerText.slice(0, 200),
  })));
} finally {
  await browser.close();
}
