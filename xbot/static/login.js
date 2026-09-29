// Déjà connecté ? direction le panneau
if (localStorage.getItem("token")) location.href = "/";

const alertBox = document.getElementById("error");
const alertText = document.getElementById("errorText");
const form = document.getElementById("loginForm");
const submit = form.querySelector("button[type=submit]");

function showError(msg) {
  alertText.textContent = msg;
  alertBox.classList.add("is-visible");
}

form.onsubmit = async (e) => {
  e.preventDefault();
  alertBox.classList.remove("is-visible");
  submit.disabled = true;
  try {
    const r = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("username").value,
        password: document.getElementById("password").value,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) { showError(data.error || "Invalid credentials"); return; }
    localStorage.setItem("token", data.token);
    localStorage.setItem("username", data.username);
    localStorage.setItem("is_admin", data.is_admin ? "1" : "");
    location.href = "/";
  } catch {
    showError("Cannot reach the server.");
  } finally {
    submit.disabled = false;
  }
};
