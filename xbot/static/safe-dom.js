"use strict";

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function safeLink(value) {
  try {
    const url = new URL(String(value));
    return ["https:", "http:"].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

// Build a new tree from formatting tags only. Never attach imported nodes or
// copy event handlers, CSS, IDs, embedded media, or arbitrary URL schemes.
function setArticleHtml(target, html) {
  const parsed = new DOMParser().parseFromString(String(html ?? ""), "text/html");
  const allowed = new Set(["P", "DIV", "SPAN", "BR", "B", "STRONG", "I", "EM",
    "U", "S", "DEL", "H1", "H2", "H3", "UL", "OL", "LI", "BLOCKQUOTE", "PRE", "CODE", "A"]);
  const blocked = new Set(["SCRIPT", "STYLE", "IFRAME", "OBJECT", "EMBED", "SVG",
    "MATH", "TEMPLATE", "FORM", "INPUT", "BUTTON", "LINK", "META", "BASE"]);
  function copy(node, parent, depth = 0) {
    if (depth > 100) return;
    if (node.nodeType === Node.TEXT_NODE) {
      parent.appendChild(document.createTextNode(node.textContent));
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE || blocked.has(node.tagName)) return;
    let dest = parent;
    if (allowed.has(node.tagName)) {
      dest = document.createElement(node.tagName.toLowerCase());
      if (node.tagName === "A") {
        const href = safeLink(node.getAttribute("href"));
        if (href) dest.setAttribute("href", href);
      }
      parent.appendChild(dest);
    }
    for (const child of node.childNodes) copy(child, dest, depth + 1);
  }
  const fragment = document.createDocumentFragment();
  for (const child of parsed.body.childNodes) copy(child, fragment);
  target.replaceChildren(fragment);
}
