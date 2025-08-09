export function initTheme(themeToggleBtn) {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  if (themeToggleBtn) themeToggleBtn.textContent = saved === "dark" ? "☀️" : "🌙";

  themeToggleBtn?.addEventListener("click", () => {
    const t = document.documentElement.getAttribute("data-theme");
    const next = t === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    themeToggleBtn.textContent = next === "dark" ? "☀️" : "🌙";
    localStorage.setItem("theme", next);
  });
}
