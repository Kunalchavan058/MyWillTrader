import { els } from "../util/dom.js";
import { getSelectedArray, removeSelected, on } from "../core/state.js";

function renderSelected(){
  const arr = getSelectedArray();
  els.selectedListEl.innerHTML = arr.map(sym => `
    <div class="selected-item" data-sym="${sym}">
      <span class="dot"></span>
      <span class="ticker">${sym}</span>
      <button type="button" class="remove-btn" data-remove="${sym}" aria-label="Remove">×</button>
    </div>
  `).join("");
}

export function initSelectedList() {
  on("selected:changed", renderSelected);
  els.selectedListEl.addEventListener("click",(e)=>{
    const btn = e.target.closest("button[data-remove]");
    if(!btn) return;
    removeSelected(btn.dataset.remove);
  });
  renderSelected();
}
