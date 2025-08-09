import { els } from "../util/dom.js";
import { getSymbols, setFiltered, addSelected, getSelectedArray } from "../core/state.js";

// Position & open/close
function openDropdown(){
  const cardRect = els.watchlistCard.getBoundingClientRect();
  const inputRect = els.searchEl.getBoundingClientRect();
  els.listEl.style.left  = (inputRect.left - cardRect.left) + "px";
  els.listEl.style.top   = (inputRect.bottom - cardRect.top + 6) + "px";
  els.listEl.style.width = inputRect.width + "px";
  els.listEl.classList.add("open");
}
function closeDropdown(){ els.listEl.classList.remove("open"); }

// Render
function renderDropdown(list){
  const items = list.map(sym => `<div class="row" data-sym="${sym}" role="option"><span class="symbol">${sym}</span></div>`).join("");
  els.listEl.innerHTML = items || `<div class="row" aria-disabled="true">No matches</div>`;
}

function excludeSelected(arr){
  const sel = new Set(getSelectedArray());
  return arr.filter(s => !sel.has(s));
}

function safeCloseOnOutside() {
  document.addEventListener("click",(e)=>{ if(!els.watchlistCard.contains(e.target)) closeDropdown(); });
}

export function initDropdown() {
  safeCloseOnOutside();

  // Show ALL (except already selected) on focus
  els.searchEl.addEventListener("focus", () => {
    renderDropdown(excludeSelected(getSymbols()));
    openDropdown();
  });

  // Filter as you type; show all matches (no cap)
  els.searchEl.addEventListener("input", () => {
    const q = els.searchEl.value.trim().toLowerCase();
    const base = getSymbols();
    const filtered = q ? base.filter(s=>s.toLowerCase().includes(q)) : base.slice();
    setFiltered(filtered);
    renderDropdown(excludeSelected(filtered));
    openDropdown();
  });

  // Click on suggestion to add
  els.listEl.addEventListener("click",(e)=>{
    const row = e.target.closest(".row[data-sym]");
    if(!row) return;
    addSelected(row.dataset.sym);
    els.searchEl.value = "";
    closeDropdown();
  });
}

// Public close for other modules (e.g., botControls)
export function closeDropdownPublic(){ closeDropdown(); }
