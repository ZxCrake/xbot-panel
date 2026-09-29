const token = localStorage.getItem("token");
if (!token || !localStorage.getItem("is_admin")) location.href = "/admin/login";

const $ = id => document.getElementById(id);
const H = { "Authorization": "Bearer " + token };
async function api(path, opts = {}) {
  // Content-Type uniquement s'il y a un corps : le serveur rejette (400) toute
  // requête annoncée en JSON dont le corps n'est pas un objet — cf. _json_object().
  const headers = { ...H, ...(opts.body ? { "Content-Type": "application/json" } : {}), ...(opts.headers || {}) };
  const r = await fetch(path, { ...opts, headers });
  if (r.status === 401) { localStorage.clear(); location.href = "/admin/login"; return null; }
  if (r.status === 403) { localStorage.removeItem("is_admin"); location.href = "/admin/login"; return null; }
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

// Password aléatoire : 16 caractères, jeu non ambigu, tirage cryptographique
function randomPassword(len = 16) {
  const chars = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%&*?";
  const buf = new Uint32Array(len);
  crypto.getRandomValues(buf);
  let out = "";
  for (let i = 0; i < len; i++) out += chars[buf[i] % chars.length];
  return out;
}

const uname = localStorage.getItem("username") || "";
$("who").textContent = uname;
$("avatar").textContent = (uname[0] || "?").toUpperCase();
$("logout").onclick = (e) => { e.preventDefault(); localStorage.clear(); location.href = "/admin/login"; };

// ── Navigation entre vues ──
const TITLES = { overview: "Overview", users: "Users" };
function showView(name) {
  document.querySelectorAll(".view").forEach(v => v.hidden = (v.id !== "view-" + name));
  document.querySelectorAll(".nav-item[data-view]").forEach(b => b.classList.toggle("active", b.dataset.view === name));
  $("pageTitle").textContent = TITLES[name] || "";
}
document.querySelectorAll(".nav-item[data-view]").forEach(b => b.onclick = () => showView(b.dataset.view));

let selectedUser = null, detail = null, activeTab = "history";

async function loadUsers() {
  const r = await api("/api/admin/users"); if (!r) return;
  const data = await r.json();
  const users = data.users;

  // Agrégats de la vue d'ensemble
  $("ov_users").textContent = users.length;
  $("ov_admins").textContent = users.filter(u => u.is_admin).length;
  const running = users.filter(u => u.running);
  $("ov_running").textContent = running.length;
  $("ov_accounts").textContent = users.reduce((a, u) => a + (u.accounts || 0), 0);
  $("userCount").textContent = users.length + (users.length > 1 ? " users" : " user");
  $("runningList").innerHTML = running.length
    ? '<div class="list">' + running.map(u =>
        `<div class="list-item static"><span class="dot on"></span>
           <b>${escapeHtml(u.username)}</b>
           <span class="muted">${u.accounts} accounts</span></div>`).join("") + "</div>"
    : '<span class="muted text-sm">No tasks running.</span>';

  // Table des users
  const body = $("usersBody"); body.innerHTML = "";
  if (!users.length) {
    body.innerHTML = '<tr><td colspan="5" class="table-empty">No users.</td></tr>';
    return;
  }
  users.forEach(u => {
    const tr = document.createElement("tr");
    tr.className = "row-interactive" + (u.username === selectedUser ? " selected" : "");
    tr.tabIndex = 0;
    tr.innerHTML =
      `<td><span class="dot ${u.running ? "on" : ""}" title="${u.running ? "Task running" : "Idle"}"></span></td>
       <td style="font-weight:500;">${escapeHtml(u.username)}</td>
       <td class="muted">${u.accounts}</td>
       <td><span class="badge ${u.is_admin ? "badge-default" : "badge-secondary"}">${u.is_admin ? "admin" : "user"}</span></td>
       <td><button class="btn btn-ghost btn-icon-sm" data-del="${escapeHtml(u.username)}" title="Revoke access" aria-label="Revoke access for ${escapeHtml(u.username)}">
             <svg class="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true" style="pointer-events:none;"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
           </button></td>`;
    tr.onclick = e => { if (e.target.closest("[data-del]")) return; selectUser(u.username); };
    tr.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectUser(u.username); } };
    body.appendChild(tr);
  });
  body.querySelectorAll("[data-del]").forEach(b => b.onclick = async ev => {
    ev.stopPropagation();
    const name = b.dataset.del;
    if (!confirm(`Revoke access for ${name} and stop their tasks?\nTheir files will be kept separately on the server.`)) return;
    const r = await api("/api/admin/users/" + name, { method: "DELETE" }); if (!r) return;
    const res = await r.json();
    if (res.error) toast(res.error, false);
    else {
      toast("Deleted: " + name);
      if (selectedUser === name) {
        selectedUser = null;
        $("detailContent").style.display = "none";
        $("detailBody").style.display = "flex";
        $("detailName").textContent = "no users";
        $("resetPassBtn").disabled = true;
      }
      loadUsers();
    }
  });
}

async function selectUser(name) {
  selectedUser = name; $("detailName").textContent = name;
  showView("users");
  loadUsers();
  const r = await api("/api/admin/users/" + name + "/detail"); if (!r) return;
  detail = await r.json();
  $("detailBody").style.display = "none"; $("detailContent").style.display = "block";
  $("resetPassBtn").disabled = false;
  renderLive(); renderTab();
}

function renderLive() {
  const l = detail.live || {};
  if (!l.action_name && !l.total) {
    $("liveStats").innerHTML = '<span class="muted text-sm">No recent task.</span>';
    return;
  }
  $("liveStats").innerHTML =
    `<span class="badge ${l.running ? "badge-success" : "badge-secondary"}">${l.running ? "running" : "stopped"}</span>
     <span class="badge badge-outline">${escapeHtml(l.action_name || "—")}</span>
     <span class="badge badge-success">${l.success || 0} succeeded</span>
     <span class="badge badge-destructive">${l.failed || 0} failed</span>
     <span class="badge badge-outline">${l.accounts_done || 0}/${l.total_accounts || 0} accounts</span>`;
}

function renderTab() {
  const hist = $("histView"), text = $("textView");
  if (activeTab === "history") {
    text.style.display = "none"; hist.style.display = "flex";
    const items = detail.history || [];
    hist.innerHTML = items.length ? items.map(h => {
      const d = new Date(h.t * 1000).toLocaleString("fr-FR");
      return `<div><span class="ts">${d}</span> <span class="${h.ok ? "ok" : "fail"}">${h.ok ? "✓" : "✗"}</span> <span class="muted">[${escapeHtml(h.action)}]</span> ${escapeHtml(h.msg)}</div>`;
    }).join("") : '<span class="muted text-sm">No activity recorded.</span>';
  } else if (activeTab === "config") {
    hist.style.display = "none"; text.style.display = "block";
    text.textContent = JSON.stringify(detail.config || {}, null, 2);
  } else {
    hist.style.display = "none"; text.style.display = "block";
    text.textContent = (detail.files && detail.files[activeTab]) || "(empty)";
  }
}

document.querySelectorAll("#detailTabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#detailTabs button").forEach(x => x.classList.remove("active"));
  b.classList.add("active"); activeTab = b.dataset.tab; renderTab();
});

$("genPassBtn").onclick = () => {
  const pw = randomPassword();
  $("newPass").value = pw;
  $("newPass").type = "text";
  navigator.clipboard && navigator.clipboard.writeText(pw)
    .then(() => toast("Password generated and copied"))
    .catch(() => toast("Password generated"));
};

$("createBtn").onclick = async () => {
  const body = { username: $("newUser").value, password: $("newPass").value, is_admin: $("newAdmin").checked };
  const r = await api("/api/admin/users", { method: "POST", body: JSON.stringify(body) }); if (!r) return;
  const d = await r.json();
  if (d.error) toast(d.error, false);
  else {
    toast("Created: " + body.username);
    $("newUser").value = ""; $("newPass").value = ""; $("newPass").type = "password";
    $("newAdmin").checked = false;
    loadUsers();
  }
};

$("resetPassBtn").onclick = async () => {
  if (!selectedUser) { toast("Select a user first", false); return; }
  const p = prompt("New password for " + selectedUser + " (randomly pre-filled, editable):", randomPassword());
  if (!p) return;
  const r = await api("/api/admin/users/" + selectedUser + "/password", { method: "POST", body: JSON.stringify({ password: p }) }); if (!r) return;
  const d = await r.json();
  toast(d.error ? d.error : "Password updated", !d.error);
};

loadUsers();
setInterval(() => {
  loadUsers();
  if (selectedUser) {
    api("/api/admin/users/" + selectedUser + "/detail")
      .then(r => r && r.json())
      .then(d => { if (d) { detail = d; renderLive(); if (activeTab === "history") renderTab(); } });
  }
}, 4000);
