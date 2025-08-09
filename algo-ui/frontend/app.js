import { els } from "./util/dom.js";
import { initTheme } from "./core/theme.js";
import { fetchTickers } from "./core/api.js";
import { setSymbols, on } from "./core/state.js";
import { initDropdown } from "./ui/dropdown.js";
import { initSelectedList } from "./ui/selectedList.js";
import { loadSettingsUI, initSettingsUI } from "./ui/settings.js";
import { initBotControls, refreshStatus } from "./ui/botControls.js";
import { renderState } from "./ui/stateTable.js";
import { connectWS } from "./util/ws.js";

async function loadTickers() {
  try{
    const list = await fetchTickers();
    setSymbols(list);
  }catch{
    els.listEl.innerHTML = `<div class="row">Failed to load tickers</div>`;
  }
}

function init() {
  initTheme(els.themeToggleBtn);
  initDropdown();
  initSelectedList();
  initSettingsUI();
  initBotControls();

  // improve a11y: close dropdown if watchlist loses focus
  document.addEventListener("keydown", (e)=>{
    if (e.key === "Escape") document.activeElement?.blur();
  });

  connectWS({ onState: renderState });

  // render updates if symbol list changes in the future (hook available)
  on("symbols:updated", () => {});
}

(async () => {
  init();
  await loadTickers();
  await loadSettingsUI();
  await refreshStatus();
})();
