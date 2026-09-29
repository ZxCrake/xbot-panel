const token = localStorage.getItem("token");
if (!token) location.href = "/login";

const $ = id => document.getElementById(id);
const H = { "Authorization": "Bearer " + token };
async function api(path, opts = {}) {
  // Content-Type uniquement s'il y a un corps : le serveur rejette (400) toute
  // requête annoncée en JSON dont le corps n'est pas un objet — cf. _json_object().
  const headers = { ...H, ...(opts.body ? { "Content-Type": "application/json" } : {}), ...(opts.headers || {}) };
  const r = await fetch(path, { ...opts, headers });
  if (r.status === 401) { localStorage.clear(); location.href = "/login"; return null; }
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    toast(d.error || `Request failed (${r.status})`, false);
    return null;
  }
  return r;
}
function toast(msg, ok = true) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.toggle("toast-err", !ok);
  t.style.display = "block";
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.style.display = "none", 2800);
}

// ── User ──
const uname = localStorage.getItem("username") || "";
$("who").textContent = uname;
$("avatar").textContent = (uname[0] || "?").toUpperCase();
if (localStorage.getItem("is_admin")) $("adminNav").style.display = "flex";
$("logout").onclick = (e) => { e.preventDefault(); localStorage.clear(); location.href = "/login"; };

// ── Navigation entre vues ──
const TITLES = {
  dashboard: "Dashboard",
  action: "New task",
  tokens: "X Accounts",
  articles: "Articles",
  scraper: "Extraction",
  config: "Settings",
  farm: "Farm",
};
let activeView = "dashboard";
function showView(name) {
  activeView = name;
  document.querySelectorAll(".view").forEach(v => v.hidden = (v.id !== "view-" + name));
  document.querySelectorAll(".nav-item[data-view]").forEach(b => b.classList.toggle("active", b.dataset.view === name));
  $("pageTitle").textContent = TITLES[name] || "";
  window.scrollTo({ top: 0, behavior: "instant" });
  if (name === "farm") { farmCfgLoaded = false; loadFarmView(); loadFarmContent(); }
}
document.querySelectorAll(".nav-item[data-view]").forEach(b => b.onclick = () => showView(b.dataset.view));

// ── Actions ──
let selectedMode = null, actionNames = {};
async function loadActions() {
  const r = await api("/api/actions"); if (!r) return;
  actionNames = await r.json();
  const list = $("actionsList"); list.innerHTML = "";
  for (const [num, name] of Object.entries(actionNames)) {
    const t = document.createElement("button");
    t.type = "button";
    t.className = "tile"; t.dataset.mode = num;
    t.innerHTML = `<span class="tile-name">${escapeHtml(name)}</span>`;
    t.onclick = () => {
      document.querySelectorAll(".tile").forEach(x => { x.classList.remove("active"); x.setAttribute("aria-pressed", "false"); });
      t.classList.add("active"); t.setAttribute("aria-pressed", "true");
      selectedMode = Number(num); refreshOptions();
    };
    list.appendChild(t);
  }
}
// Blocs d'options affichés selon l'action
const TWEET_ID_ACTIONS = [2, 3, 4, 5, 6];
function refreshOptions() {
  const m = selectedMode;
  const show = {
    opt_tweetids: TWEET_ID_ACTIONS.includes(m),
    opt_quote:    m === 1,
    opt_direct:   m === 12 || m === 13,
    opt_reply:    m === 4,
    opt_pfp:      m === 8,
    opt_profile:  m === 9,
  };
  $("opt_dmmsg").hidden = (m !== 13);
  $("directHint").textContent = m === 12
    ? "Each account follows its allotted targets. Combine with “Profile picture” and “Name/Bio”: the “followed you” notification then shows the account name and picture."
    : "Each account DMs its allotted targets: the message lands as a “message request”, which triggers a notification even from a stranger.";
  $("optWrap").style.display = m ? "flex" : "none";
  let any = false;
  for (const [id, on] of Object.entries(show)) { $(id).style.display = on ? "block" : "none"; if (on) any = true; }
  $("optEmpty").style.display = any ? "none" : "block";
  $("optTitle").textContent = m ? (actionNames[m] + " — options") : "Action options";
  $("runSummary").textContent = m ? ("Action : " + actionNames[m]) : "Select an action above";
  if (m) loadActionFields(m);
}

// Pré-remplit les champs avec le contenu actuel des fichiers
function jsonToLines(txt) { try { return (JSON.parse(txt || "[]") || []).map(o => o.text || "").join("\n"); } catch { return ""; } }
async function loadActionFields(m) {
  if (TWEET_ID_ACTIONS.includes(m)) {
    const r = await api("/api/file/tweet_ids.txt"); if (r) $("act_tweetids").value = (await r.json()).content || "";
  }
  if (m === 1) {
    let r = await api("/api/file/tweets.txt"); if (r) $("act_tweets").value = jsonToLines((await r.json()).content);
    r = await api("/api/file/users.txt"); if (r) $("act_mentions").value = (await r.json()).content || "";
  }
  if (m === 12 || m === 13) {
    let r = await api("/api/file/users.txt"); if (r) $("act_direct_users").value = (await r.json()).content || "";
    if (m === 13) { const r2 = await api("/api/file/dms.txt"); if (r2) $("act_dms").value = jsonToLines((await r2.json()).content); }
  }
  if (m === 4) {
    const r = await api("/api/file/reply.txt"); if (r) $("act_replies").value = jsonToLines((await r.json()).content);
  }
}

// ── Settings ──
const CFG = ["proxy", "proxies", "proxy_mode", "threads", "limit", "delay_min", "delay_max", "select_users", "follow_mentioned", "mentions_per_target", "random_mention_position", "pfp_image", "display_name", "bio"];
function syncProxyModeUI() { const m = $("cfg_proxy_mode"), r = $("proxyRotateRow"); if (m && r) r.style.display = m.value === "rotating" ? "" : "none"; }
if ($("cfg_proxy_mode")) $("cfg_proxy_mode").addEventListener("change", syncProxyModeUI);
if ($("rotateProxyBtn")) $("rotateProxyBtn").onclick = async () => { if (!confirm("Assign a fresh sticky session (new exit IP) to every account?")) return; const r = await api("/api/proxy/rotate-sessions", { method: "POST", body: "{}" }); if (r) toast("Proxy sessions rotated — new exit IPs assigned"); };
function collectConfig() { const c = {}; CFG.forEach(f => { const el = $("cfg_" + f); if (!el) return; c[f] = el.type === "checkbox" ? (el.checked ? 1 : 0) : (el.type === "number" ? Number(el.value) : el.value); }); return c; }
async function loadConfig() { const r = await api("/api/config"); if (!r) return; const c = await r.json(); CFG.forEach(f => { const el = $("cfg_" + f); if (el && c[f] !== undefined) { if (el.type === "checkbox") el.checked = !!c[f]; else el.value = c[f]; } }); syncProxyModeUI(); }
$("saveCfgBtn").onclick = async () => { const r = await api("/api/config", { method: "POST", body: JSON.stringify(collectConfig()) }); if (r) toast("Settings saved"); };

// ── X Accounts ──
async function loadAccounts() {
  const r = await api("/api/file/accounts.txt"); if (!r) return;
  const c = (await r.json()).content || "";
  $("acctEditor").value = c;
  const n = c.split("\n").filter(l => l.trim()).length;
  $("acctCount").textContent = n || "";
  $("acctCountCard").textContent = n;
}
$("saveAcctBtn").onclick = async () => {
  const r = await api("/api/file/accounts.txt", { method: "POST", body: JSON.stringify({ content: $("acctEditor").value }) });
  if (!r) return;
  loadAccounts(); toast("Accounts saved");
};

// ── Import de la photo de profil ──
$("uploadPfpBtn").onclick = async () => {
  const f = $("pfpFile").files[0]; if (!f) { toast("Choose an image", false); return; }
  const fd = new FormData(); fd.append("file", f);
  const r = await fetch("/api/upload-pfp", { method: "POST", headers: { "Authorization": "Bearer " + token }, body: fd });
  const d = await r.json().catch(() => ({}));
  toast(d.ok ? ("Image uploaded: " + d.saved) : ("Error: " + (d.error || r.status)), !!d.ok);
};

// ── Lancer / Stop ──
const linesToJson = t => JSON.stringify(t.split("\n").map(s => s.trim()).filter(Boolean).map(text => ({ text })));
const saveFile = (name, content) => api("/api/file/" + name, { method: "POST", body: JSON.stringify({ content }) });
$("runBtn").onclick = async () => {
  const m = selectedMode;
  if (!m) { toast("Select an action", false); return; }
  // Persiste les champs du formulaire dans les fichiers que lit le runner
  if (TWEET_ID_ACTIONS.includes(m)) {
    const ids = $("act_tweetids").value.split("\n").map(extractTweetId).filter(Boolean);
    if (!ids.length) { toast("Add at least one post link or ID", false); return; }
    if (!await saveFile("tweet_ids.txt", ids.join("\n"))) return;
  }
  if (m === 1) {
    if (!$("act_tweets").value.trim()) { toast("Add at least one message", false); return; }
    if (!await saveFile("tweets.txt", linesToJson($("act_tweets").value))) return;
    if (!await saveFile("users.txt", $("act_mentions").value.split("\n").map(s => s.trim().replace(/^@/, "")).filter(Boolean).join("\n"))) return;
  }
  if (m === 12 || m === 13) {
    if (!$("act_direct_users").value.trim()) { toast("Add at least one target account", false); return; }
    if (!await saveFile("users.txt", $("act_direct_users").value.split("\n").map(s => s.trim().replace(/^@/, "")).filter(Boolean).join("\n"))) return;
    if (m === 13) {
      if (!$("act_dms").value.trim()) { toast("Add at least one private message", false); return; }
      if (!await saveFile("dms.txt", linesToJson($("act_dms").value))) return;
    }
  }
  if (m === 4) {
    if (!$("act_replies").value.trim()) { toast("Add at least one reply text", false); return; }
    if (!await saveFile("reply.txt", linesToJson($("act_replies").value))) return;
  }
  const r = await api("/api/run", { method: "POST", body: JSON.stringify({ action_mode: m, config: collectConfig() }) });
  if (!r) return; const d = await r.json();
  if (d.error) { toast("Error: " + d.error, false); }
  else { toast("Task started"); showView("dashboard"); }
};
$("stopBtn").onclick = async () => {
  const r = await api("/api/stop", { method: "POST" }); if (!r) return;
  const d = await r.json();
  toast(d.error ? d.error : "Stop requested", !d.error);
};

// ── Sondage de l'état ──
function fmt(s) { return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0"); }
function setStat(id, val) {
  const el = $(id);
  if (el.textContent !== String(val)) {
    el.textContent = val;
    el.classList.remove("bump"); void el.offsetWidth; el.classList.add("bump");
  }
}
async function poll() {
  const r = await api("/api/status"); if (!r) return;
  const s = await r.json();
  setStat("s_success", s.success || 0);
  setStat("s_failed", s.failed || 0);
  setStat("s_hidden", s.hidden || 0);
  $("s_total").textContent = s.total || 0;
  setStat("s_rate", (s.rate || 0) + "%");
  setStat("s_accounts", (s.accounts_done || 0) + "/" + (s.total_accounts || 0));
  $("s_elapsed").textContent = fmt(s.elapsed || 0);

  const running = !!s.running;
  $("runState").textContent = running ? (s.action_name || "Running") : "Idle";
  $("runDot").classList.toggle("on", running);
  $("runDot2").classList.toggle("on", running);
  $("sideDot").classList.toggle("on", running);
  $("sideState").textContent = running ? "Running" : "Idle";
  $("sideSub").textContent = running ? fmt(s.elapsed || 0) : "—";
  $("jobTitle").textContent = running ? ("Running: " + (s.action_name || "")) : "No task running";
  $("jobBanner").classList.toggle("active", running);
  $("runBtn").disabled = running;
  $("stopBtn").disabled = !running;

  if (s.log) $("log").innerHTML = s.log.slice().reverse().map(l =>
    `<div class="${l.ok ? "ok" : "fail"}"><span class="lg-mark">${l.ok ? "✓" : "✗"}</span><span>${escapeHtml(l.msg)}</span></div>`
  ).join("");
}
setInterval(poll, 1500);

// ── Farm (réchauffement autonome) ──
function farmStateChip(running, run) {
  const el = $("farmRunning");
  if (running) {
    el.textContent = "Status: running";
    if (run && run.duration_days)
      el.textContent = `Status: running — day ${run.day_index}/${run.duration_days}`;
  } else if (run && run.completed) {
    el.textContent = `Status: completed (ran ${run.duration_days} days)`;
  } else {
    el.textContent = "Status: stopped";
  }
  $("farmBadge").textContent = running ? "on" : "";
  if (!running && $("farmEngine")) $("farmEngine").textContent = "";

  const startBtn = $("farmStartBtn");
  if (startBtn) startBtn.textContent =
    (!running && run && run.completed) ? "Restart with same settings" : "Start the farm";
}
function renderFarmEngine(d) {
  const el = $("farmEngine");
  if (!el) return;
  if (!d.running) { el.textContent = ""; return; }
  const e = d.engine || {};
  const now = d.now || Date.now() / 1000;
  const parts = [];
  if (e.last_tick) {
    const ago = Math.max(0, Math.round(now - e.last_tick));
    parts.push(ago < 180 ? `engine alive (tick ${ago}s ago)` : `engine stalled? (last tick ${ago}s ago)`);
  } else {
    parts.push("engine starting…");
  }
  if (typeof e.planned === "number" && e.planned > 0)
    parts.push(`today: ${e.done || 0}/${e.planned} done` + ((e.failed || 0) ? `, ${e.failed} failed` : ""));
  if (e.reason === "waiting" && e.next_due) {
    const mins = Math.max(1, Math.round((e.next_due - now) / 60));
    const clock = new Date(e.next_due * 1000).toISOString().slice(11, 16);
    parts.push(`next action in ~${mins} min (${clock} UTC)`);
  }
  else if (e.reason === "waiting") parts.push("waiting for scheduled actions");
  else if (e.reason === "plan_exhausted") parts.push("today's plan finished");
  else if (e.reason === "no_content") parts.push("no actions planned — fill the Life content channels below");
  else if (e.reason === "no_accounts") parts.push("no accounts imported");
  else if (e.reason === "no_active_accounts") parts.push("all accounts paused (auth) — see table below");
  else if (e.reason === "completed") parts.push("run completed");
  else if (e.reason === "invalid_cfg") parts.push("invalid farm config — stop the farm and start a new run with the settings below");
  el.textContent = " · " + parts.join(" · ");
}
function renderFarmRows(accounts) {
  const tb = $("farmScoresBody");
  if (!accounts || !accounts.length) {
    tb.innerHTML = '<tr><td colspan="8" class="field-description" style="padding:0.5rem;">—</td></tr>';
    return;
  }
  const labelClass = { ready: "ok", warming: "", dormant: "", compromised: "fail" };
  tb.innerHTML = accounts.map(a => {
    const done = Object.entries(a.done || {}).map(([k, v]) => `${escapeHtml(k)}:${v}`).join(" ") || "—";
    const sc = a.label === "compromised" ? "compromised" : escapeHtml(a.label || "");
    let eta;
    if (a.label === "ready") eta = "ready";
    else if (a.status === "compromised") eta = "—";
    else if (typeof a.eta_days === "number") eta = `≈ ${Math.max(0.1, a.eta_days).toFixed(a.eta_days >= 10 ? 0 : 1)} d`;
    else eta = escapeHtml(a.eta_note || "—");
    return `<tr style="border-bottom:1px solid var(--border);">
      <td style="padding:0.35rem 0.5rem;">@${escapeHtml(a.account)}</td>
      <td style="padding:0.35rem 0.5rem;"><b>${a.score}</b></td>
      <td style="padding:0.35rem 0.5rem;" class="${labelClass[a.label] || ""}">${sc}</td>
      <td style="padding:0.35rem 0.5rem;">${a.followers}${a.growth > 0 ? ` (+${a.growth})` : ""}</td>
      <td style="padding:0.35rem 0.5rem;">${a.active_days} / 14</td>
      <td style="padding:0.35rem 0.5rem;">${a.tweets_ok} / ${a.tweets_flagged}</td>
      <td style="padding:0.35rem 0.5rem;">${eta}</td>
      <td style="padding:0.35rem 0.5rem;">${done}</td>
    </tr>`;
  }).join("");
}
function farmCount(id, n) { $(id).textContent = n ? `(${n} line${n > 1 ? "s" : ""})` : "(empty)"; }
function farmCountLines() {
  farmCount("farm_users_count", $("farm_users").value.split("\n").filter(l => l.trim()).length);
  farmCount("farm_ids_count", $("farm_ids").value.split("\n").filter(l => l.trim()).length);
  farmCount("farm_tweets_count", $("farm_tweets").value.split("\n").filter(l => l.trim()).length);
}
async function loadFarmContent() {
  let r = await api("/api/file/users.txt");   if (r) $("farm_users").value  = (await r.json()).content || "";
  r = await api("/api/file/tweet_ids.txt");   if (r) $("farm_ids").value    = (await r.json()).content || "";
  r = await api("/api/file/tweets.txt");      if (r) $("farm_tweets").value = jsonToLines((await r.json()).content);
  farmCountLines();
}
["farm_users", "farm_ids", "farm_tweets"].forEach(id => $(id).addEventListener("input", farmCountLines));
$("farmSaveContentBtn").onclick = async () => {
  const state = $("farmContentState");
  let r = await saveFile("users.txt", $("farm_users").value);    if (!r) { state.textContent = "failed: accounts to follow"; return; }
  r = await saveFile("tweet_ids.txt", $("farm_ids").value);      if (!r) { state.textContent = "failed: tweets to read"; return; }
  let tw;
  try { tw = linesToJson($("farm_tweets").value); } catch (e) { state.textContent = "posts : " + e.message; return; }
  r = await saveFile("tweets.txt", tw);                          if (!r) { state.textContent = "failed: organic posts"; return; }
  state.textContent = "content saved";
  toast("Farm content saved", true);
  farmCountLines();
};
// pré-remplit les champs avec la dernière config utilisée (une fois par entrée dans la vue)
let farmCfgLoaded = false;
function fillFarmCfg(cfg) {
  if (farmCfgLoaded || !cfg || !cfg.duration_days || !cfg.actions) return false;
  $("farmDurationDays").value = cfg.duration_days;
  $("farmVarMin").value = cfg.variation_min ?? 80;
  $("farmVarMax").value = cfg.variation_max ?? 100;
  for (const [kind, id] of FARM_ACTIONS) $(id).value = cfg.actions[kind] ?? 0;
  farmCfgLoaded = true;
  return true;
}
async function loadFarmView() {
  let r = await api("/api/farm/scores"); if (r) { const d = await r.json(); farmStateChip(d.running, d.run); renderFarmRows(d.accounts); }
  r = await api("/api/farm/status"); if (r) {
    const d = await r.json();
    if (typeof d.media_count === "number") $("farm_media_count").textContent = `(${d.media_count} in bank)`;
    farmStateChip(d.running, d.run);
    renderFarmEngine(d);
    fillFarmCfg(d.cfg);
    if (d.log) $("farmLog").innerHTML = d.log.slice().reverse().slice(0, 150)
      .map(l => `<div><span>${escapeHtml(l.msg)}</span></div>`).join("");
  }
}
const FARM_ACTIONS = [
  ["follow",   "farmCntFollow"],
  ["like",     "farmCntLike"],
  ["retweet",  "farmCntRetweet"],
  ["bookmark", "farmCntBookmark"],
  ["view",     "farmCntView"],
  ["tweet",    "farmCntTweet"],
];
// volumes par défaut d'une journée « banale » — édite après avoir cliqué.
const FARM_PRESETS = {
  slow:   { follow: 0, like: 1, retweet: 0, bookmark: 0, view: 2, tweet: 0, var_min: 50, var_max: 100 },
  gentle: { follow: 1, like: 1, retweet: 0, bookmark: 0, view: 2, tweet: 0, var_min: 60, var_max: 100 },
  normal: { follow: 1, like: 2, retweet: 0, bookmark: 0, view: 2, tweet: 0, var_min: 60, var_max: 100 },
  fast:   { follow: 2, like: 4, retweet: 1, bookmark: 1, view: 4, tweet: 1, var_min: 70, var_max: 100 },
};
document.querySelectorAll("[data-farm-preset]").forEach(b => b.onclick = () => {
  const p = FARM_PRESETS[b.dataset.farmPreset]; if (!p) return;
  for (const [kind, id] of FARM_ACTIONS) $(id).value = p[kind] ?? 0;
  $("farmVarMin").value = p.var_min; $("farmVarMax").value = p.var_max;
});

function collectFarmCfg() {
  const dur = parseInt($("farmDurationDays").value, 10);
  if (!dur || dur < 1 || dur > 365) { toast("Run duration must be 1–365 days", false); return null; }
  const var_min = parseInt($("farmVarMin").value, 10), var_max = parseInt($("farmVarMax").value, 10);
  if (!var_min || !var_max || var_min < 1 || var_max > 100 || var_min > var_max) {
    toast("Variation must be within 1–100% with min ≤ max", false); return null;
  }
  const actions = {};
  let total = 0;
  for (const [kind, id] of FARM_ACTIONS) {
    const n = parseInt($(id).value, 10) || 0;
    if (n < 0 || n > 100) { toast(`${kind}: count must be 0–100`, false); return null; }
    actions[kind] = n; total += n;
  }
  if (total === 0) { toast("Enable at least one action (all counts are 0)", false); return null; }
  if (total > 100) { toast("Total actions per account per day must stay under 100", false); return null; }
  return { duration_days: dur, actions, variation_min: var_min, variation_max: var_max };
}
$("farmStartBtn").onclick = async () => {
  const cfg = collectFarmCfg(); if (!cfg) return;
  const r = await api("/api/farm/start", { method: "POST", body: JSON.stringify(cfg) });
  if (!r) return; const d = await r.json();
  toast(d.error ? ("Error: " + d.error) : "Farm started", !d.error);
  loadFarmView();
};
$("farmStopBtn").onclick = async () => {
  const r = await api("/api/farm/stop", { method: "POST" });
  if (!r) return; const d = await r.json();
  toast(d.error ? ("Error: " + d.error) : "Farm stopped", !d.error);
  loadFarmView();
};
$("farmRefreshBtn").onclick = loadFarmView;
setInterval(() => { if (activeView === "farm") loadFarmView(); }, 10000);

async function farmGen(channel, taId, extra = {}) {
  const r = await api("/api/farm/generate", {
    method: "POST", body: JSON.stringify({ channel, ...extra }),
  });
  if (!r) return;
  const d = await r.json();
  if (d.error) { toast("Error: " + d.error, false); return; }
  const ta = $(taId);
  const merged = ta.value.split("\n").map(l => l.trim()).filter(Boolean);
  const seen = new Set(merged);
  let added = 0;
  (d.lines || []).forEach(l => { if (!seen.has(l)) { seen.add(l); merged.push(l); added++; } });
  ta.value = merged.join("\n") + "\n";
  farmCountLines();
  toast(added + " lines added", true);
}
$("farmGenUsers").onclick = () => farmGen("users", "farm_users");
$("farmGenIds").onclick = () => farmGen("tweet_ids", "farm_ids");
$("farmGenTweets").onclick = () => farmGen("posts", "farm_tweets", { lang: $("farmGenLang").value });
$("farmGenMedia").onclick = async () => {
  const r = await api("/api/farm/generate", { method: "POST", body: JSON.stringify({ channel: "media", count: 10 }) });
  if (!r) return;
  const d = await r.json();
  if (d.error) { toast("Error: " + d.error, false); return; }
  toast(`${d.added} images added (${d.total} in bank)`, true);
  loadFarmView();
};

// ── Articles ──
let articles = [], artIdx = -1;
async function loadArticles() {
  const r = await api("/api/articles"); if (!r) return;
  articles = (await r.json()).articles || [];
  renderArtList();
}
function renderArtList() {
  const el = $("artList");
  if (!articles.length) {
    el.innerHTML = '<p class="field-description" style="margin:0;">No articles yet. Click “New”.</p>';
    return;
  }
  el.innerHTML = articles.map((a, i) =>
    `<button type="button" class="list-item${i === artIdx ? " active" : ""}" data-i="${i}">
       <svg class="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>
       <span>${escapeHtml(a.title || "sans titre")}</span>
     </button>`
  ).join("");
  el.querySelectorAll(".list-item").forEach(d => d.onclick = () => selectArt(Number(d.dataset.i)));
}
function selectArt(i) {
  artIdx = i; const a = articles[i] || {};
  $("artTitle").value = a.title || ""; $("artSubtitle").value = a.subtitle || ""; setArticleHtml($("artBody"), a.body);
  renderArtList();
}
$("artNewBtn").onclick = () => { articles.push({ title: "Nouvel article", subtitle: "", body: "" }); selectArt(articles.length - 1); };
$("artSaveBtn").onclick = async () => {
  if (artIdx < 0) { toast("Create an article first", false); return; }
  articles[artIdx] = { title: $("artTitle").value, subtitle: $("artSubtitle").value, body: $("artBody").innerHTML };
  const r = await api("/api/articles", { method: "POST", body: JSON.stringify({ articles }) });
  if (!r) return; const d = await r.json();
  toast(d.error ? ("Error: " + d.error) : ("Saved (" + d.count + " articles)"), !d.error);
  renderArtList();
};
$("artDeleteBtn").onclick = async () => {
  if (artIdx < 0) return;
  articles.splice(artIdx, 1); artIdx = -1;
  $("artTitle").value = $("artSubtitle").value = ""; $("artBody").innerHTML = "";
  await api("/api/articles", { method: "POST", body: JSON.stringify({ articles }) });
  renderArtList(); toast("Article deleted");
};
$("artImportBtn").onclick = async () => {
  const raw = prompt('Collez un tableau JSON, par ex. [{"title":"…","body":"…"}]');
  if (!raw) return;
  try {
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) throw 0;
    articles = arr.map(a => ({ title: a.title || "", subtitle: a.subtitle || "", body: a.body || "" }));
    const r = await api("/api/articles", { method: "POST", body: JSON.stringify({ articles }) });
    if (r) { artIdx = -1; renderArtList(); toast(articles.length + " articles imported"); }
  } catch { toast("Invalid JSON", false); }
};
$("artExportBtn").onclick = () => {
  const blob = new Blob([JSON.stringify(articles, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob); const a = document.createElement("a");
  a.href = url; a.download = "articles.json"; a.click(); URL.revokeObjectURL(url);
};

// ── « Fonts » Unicode (X ne gère que du texte brut : on substitue les caractères) ──
function buildMap(u, l, d) {
  const m = {};
  for (let i = 0; i < 26; i++) { m[String.fromCharCode(65 + i)] = String.fromCodePoint(u + i); m[String.fromCharCode(97 + i)] = String.fromCodePoint(l + i); }
  if (d) for (let i = 0; i < 10; i++) m[String(i)] = String.fromCodePoint(d + i);
  return m;
}
const FONTS = {
  bold: buildMap(0x1D400, 0x1D41A, 0x1D7CE),
  italic: buildMap(0x1D434, 0x1D44E, 0),
  boldItalic: buildMap(0x1D468, 0x1D482, 0),
  mono: buildMap(0x1D670, 0x1D68A, 0x1D7F6),
};
FONTS.italic["h"] = "ℎ";  // l'italique « h » occupe un emplacement réservé
// Tables inverses pour la remise à plat (stylé → brut)
const REVERSE = {};
Object.values(FONTS).forEach(m => Object.entries(m).forEach(([plain, styled]) => { REVERSE[styled] = plain; }));
function styleText(str, name) {
  if (name === "reset") return [...str].map(c => REVERSE[c] || c).join("");
  const m = FONTS[name]; return [...str].map(c => m[c] || c).join("");
}

// Applique une police Unicode à la sélection d'un <textarea>
function fontOnTextarea(ta, name) {
  const s = ta.selectionStart, e = ta.selectionEnd;
  if (s === e) { toast("Select some text first", false); return; }
  ta.value = ta.value.slice(0, s) + styleText(ta.value.slice(s, e), name) + ta.value.slice(e);
  ta.focus(); ta.setSelectionRange(s, ta.selectionStart);
}
document.querySelectorAll(".msgFontBar button[data-font]").forEach(b =>
  b.onclick = () => fontOnTextarea($(b.closest(".msgFontBar").dataset.target), b.dataset.font));

// ── Barre d'outils de l'éditeur d'article (contenteditable) ──
function fontOnEditable(name) {
  const sel = window.getSelection();
  if (!sel.rangeCount || sel.isCollapsed) { toast("Select some text first", false); return; }
  document.execCommand("insertText", false, styleText(sel.toString(), name));
}
document.querySelectorAll("#artToolbar button").forEach(b => {
  b.onmousedown = (e) => e.preventDefault();  // conserve la sélection dans l'éditeur
  b.onclick = () => {
    $("artBody").focus();
    if (b.dataset.cmd) document.execCommand(b.dataset.cmd, false, null);
    else if (b.dataset.block) document.execCommand("formatBlock", false, b.dataset.block);
    else if (b.dataset.font) fontOnEditable(b.dataset.font);
  };
});
$("artLinkBtn").onmousedown = (e) => e.preventDefault();
$("artLinkBtn").onclick = () => {
  const input = prompt("URL du lien (https://…) :"); if (!input) return;
  const url = safeLink(input);
  if (!url) { toast("Only HTTP and HTTPS links are allowed", false); return; }
  const sel = window.getSelection();
  $("artBody").focus();
  if (sel && !sel.isCollapsed) {
    document.execCommand("createLink", false, url);
  } else {
    const text = prompt("Text to display for the link:", url) || url;
    document.execCommand("insertHTML", false,
      `<a href="${url.replace(/"/g, "&quot;")}">${escapeHtml(text)}</a>`);
  }
};

// ── Extraction ──
let scData = null;
function extractTweetId(s) {
  s = (s || "").trim();
  const m = s.match(/status(?:es)?\/(\d+)/i);
  if (m) return m[1];
  return /^\d+$/.test(s) ? s : null;
}
$("scRunBtn").onclick = async () => {
  const tid = extractTweetId($("scTweetId").value);
  if (!tid) { toast("Paste a post link or a numeric ID", false); return; }
  const targets = [...document.querySelectorAll(".sc-t:checked")].map(c => c.value);
  if (!targets.length) { toast("Select at least one type", false); return; }

  const btn = $("scRunBtn"), label = btn.querySelector(".btn-label");
  btn.disabled = true; label.textContent = "Extracting…";
  const r = await api("/api/scrape", { method: "POST", body: JSON.stringify({ tweet_id: tid, targets, max_results: Number($("scMax").value) || 500 }) });
  btn.disabled = false; label.textContent = "Extract";

  if (!r) return;
  const d = await r.json();
  if (d.error) { toast("Error: " + d.error, false); return; }
  scData = d; renderScrape(d);
};
function renderScrape(d) {
  $("scResultsPanel").style.display = "flex";
  $("scResultsTitle").textContent = "Results — post " + d.tweet_id;
  const labels = { likes: "Likes", retweets: "Retweets", replies: "Replies", quotes: "Quotes" };
  $("scResults").innerHTML = Object.entries(d.results).map(([k, v]) => {
    if (v.error) {
      return `<div class="result-group"><div class="result-group-head">${labels[k] || k}
        <span class="badge badge-destructive">${escapeHtml(v.error)}</span></div></div>`;
    }
    const items = v.items || [];
    const rows = items.map(u =>
      `<div class="list-item static"><span class="mono">@${escapeHtml(u.username)}</span>
         <span class="muted">${escapeHtml(u.name || "")}</span></div>`).join("");
    return `<div class="result-group">
      <div class="result-group-head">${labels[k] || k} <span class="badge badge-secondary">${items.length}</span></div>
      <div class="scroll-area">${rows || '<span class="muted text-sm">no results</span>'}</div>
    </div>`;
  }).join("");
}
$("scExportBtn").onclick = () => {
  if (!scData) return;
  let csv = "type,username,name\n";
  for (const [k, v] of Object.entries(scData.results))
    for (const u of (v.items || []))
      csv += `${k},${u.username},"${(u.name || "").replace(/"/g, '""')}"\n`;
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob); const a = document.createElement("a");
  a.href = url; a.download = `scrape_${scData.tweet_id}.csv`; a.click(); URL.revokeObjectURL(url);
};

// ── Import de comptes ──
let impFieldOrder = [];
function renderImpOrder() {
  $("impOrder").textContent = impFieldOrder.length ? impFieldOrder.join(" : ") : "(no field selected)";
  document.querySelectorAll("#impFields button").forEach(b =>
    b.classList.toggle("active", impFieldOrder.includes(b.dataset.f)));
}
document.querySelectorAll("#impFields button").forEach(b => b.onclick = () => {
  const f = b.dataset.f;
  if (impFieldOrder.includes(f)) impFieldOrder = impFieldOrder.filter(x => x !== f);
  else impFieldOrder.push(f);
  renderImpOrder();
});
$("impReset").onclick = () => { impFieldOrder = []; renderImpOrder(); };
$("impFile").onchange = () => {
  const f = $("impFile").files[0]; if (!f) return;
  const rd = new FileReader();
  rd.onload = () => { $("impContent").value = rd.result; toast("File loaded — review then import"); };
  rd.readAsText(f);
};
$("impBtn").onclick = async () => {
  if (!impFieldOrder.includes("AUTH_TOKEN")) { toast("AUTH_TOKEN is required in the structure", false); return; }
  const content = $("impContent").value.trim();
  if (!content) { toast("Paste or import accounts first", false); return; }
  const r = await api("/api/import-accounts", { method: "POST", body: JSON.stringify({
    fields: impFieldOrder, separator: $("impSep").value || ":", mode: $("impMode").value, content
  })});
  if (!r) return; const d = await r.json();
  if (d.error) { toast("Error: " + d.error, false); return; }
  toast(`${d.imported} accounts imported` + (d.errors ? ` (${d.errors} skipped)` : ""));
  loadAccounts();
};
renderImpOrder();

loadActions(); loadConfig(); loadAccounts(); loadArticles(); poll();

$("artBody").addEventListener("paste", e => {
  e.preventDefault();
  document.execCommand("insertText", false, e.clipboardData.getData("text/plain"));
});
$("artBody").addEventListener("drop", e => e.preventDefault());
