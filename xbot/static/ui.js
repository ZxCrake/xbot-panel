"use strict";

/* ──────────────────────────────────────────────────────────────────────────
   Thème — appliqué immédiatement (ce script est chargé de façon synchrone
   dans <head>) pour éviter tout flash de thème clair au chargement.
   La CSP interdit les scripts inline, d'où ce fichier dédié.
   ────────────────────────────────────────────────────────────────────────── */
(function () {
  var stored = null;
  try { stored = localStorage.getItem("theme"); } catch (e) { /* stockage bloqué */ }
  var dark = stored ? stored === "dark"
    : window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.classList.toggle("dark", dark);
})();

/* Mode confidentialité — floute les données sensibles pour les captures
   d'écran. Activé par défaut ; préférence persistée comme le thème. */
(function () {
  var p = null;
  try { p = localStorage.getItem("xbot_privacy"); } catch (e) { /* stockage bloqué */ }
  document.documentElement.classList.toggle("privacy", p !== "0");
})();

function setPrivacy(on) {
  document.documentElement.classList.toggle("privacy", on);
  try { localStorage.setItem("xbot_privacy", on ? "1" : "0"); } catch (e) { /* ignore */ }
  document.querySelectorAll("[data-privacy-toggle]").forEach(function (b) {
    b.setAttribute("aria-pressed", String(on));
    b.setAttribute("aria-label", on ? "Show sensitive data" : "Hide sensitive data (screenshot-safe)");
    b.setAttribute("title", on ? "Show sensitive data" : "Hide sensitive data (screenshot-safe)");
    b.innerHTML = uiIcon(on ? "eye-off" : "eye", "icon-sm");
  });
}

function setTheme(dark) {
  document.documentElement.classList.toggle("dark", dark);
  try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch (e) { /* ignore */ }
  document.querySelectorAll("[data-theme-toggle]").forEach(function (b) {
    b.setAttribute("aria-pressed", String(dark));
    b.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  });
}

/* ──────────────────────────────────────────────────────────────────────────
   Icônes — jeu Lucide, celui utilisé par shadcn/ui.
   ────────────────────────────────────────────────────────────────────────── */
const UI_ICONS = {
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  logo: '<path d="M4 4h5l11 16h-5z"/><path d="m4 20 6.5-7.5M13.5 11 20 4"/>',
  dashboard: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  "user-plus": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/>',
  file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  settings: '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
  check: '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
  "circle-x": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
  percent: '<line x1="19" x2="5" y1="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
  activity: '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  stop: '<rect width="18" height="18" x="3" y="3" rx="2"/>',
  save: '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
  refresh: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
  menu: '<line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/>',
  arrow: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  back: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
  lock: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  key: '<path d="m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4"/><path d="m21 2-9.6 9.6"/><circle cx="7.5" cy="15.5" r="5.5"/>',
  eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
  "eye-off": '<path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9"/>',
  link: '<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><line x1="8" x2="16" y1="12" y2="12"/>',
  spinner: '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>'
};

function uiIcon(name, cls) {
  const body = UI_ICONS[name] || UI_ICONS.dashboard;
  return `<svg class="icon${cls ? " " + cls : ""}" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
}

/* ──────────────────────────────────────────────────────────────────────────
   Comportements partagés
   ────────────────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  // Bascule de thème
  document.querySelectorAll("[data-theme-toggle]").forEach(b => {
    b.setAttribute("aria-pressed", String(document.documentElement.classList.contains("dark")));
    b.addEventListener("click", () => setTheme(!document.documentElement.classList.contains("dark")));
  });

  // Bascule du mode confidentialité
  document.querySelectorAll("[data-privacy-toggle]").forEach(b =>
    b.addEventListener("click", () => setPrivacy(!document.documentElement.classList.contains("privacy"))));
  if (document.querySelector("[data-privacy-toggle]"))
    setPrivacy(document.documentElement.classList.contains("privacy"));

  // Tiroir de navigation (mobile)
  const trigger = document.querySelector(".sidebar-trigger");
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.querySelector(".sidebar-overlay");
  const setMenu = open => {
    sidebar?.classList.toggle("is-open", open);
    overlay?.classList.toggle("is-open", open);
    trigger?.setAttribute("aria-expanded", String(open));
  };
  trigger?.addEventListener("click", () => setMenu(!sidebar.classList.contains("is-open")));
  overlay?.addEventListener("click", () => setMenu(false));
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && sidebar?.classList.contains("is-open")) { setMenu(false); trigger?.focus(); }
  });
  document.querySelectorAll(".nav-item[data-view]").forEach(el => el.addEventListener("click", () => setMenu(false)));

  // Shortcuts de navigation entre vues
  document.querySelectorAll("[data-go-view]").forEach(el =>
    el.addEventListener("click", () => { showView(el.dataset.goView); setMenu(false); }));

  // Afficher / masquer les mots de passe
  document.querySelectorAll(".password-toggle").forEach(button => button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.target);
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.setAttribute("aria-pressed", String(show));
    button.setAttribute("aria-label", show ? "Hide password" : "Show password");
  }));
});
