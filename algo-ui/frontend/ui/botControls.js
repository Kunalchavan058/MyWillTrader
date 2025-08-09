import { els } from "../util/dom.js";
import { fetchBotStatus, startBot, stopBot } from "../core/api.js";
import { closeDropdownPublic } from "./dropdown.js";
import { getSelectedArray } from "../core/state.js";
import { saveSelection } from "../core/api.js";

function setStatus(stateText){
  const running = String(stateText).toLowerCase().includes("run");
  els.startBtn.classList.toggle("is-on", running);
  els.startBtn.querySelector(".lbl").textContent = running ? "Running" : "Start";
  els.stopBtn.classList.toggle("running", running);
  els.stopBtn.querySelector(".lbl").textContent = running ? "Stop" : "Stopped";
}

export async function refreshStatus() {
  try{
    const data = await fetchBotStatus();
    setStatus(data.running ? "Running" : "Stopped");
    if (els.afterHoursToggleHead) els.afterHoursToggleHead.checked = !!data.test_mode;
  }catch{ setStatus("Unknown"); }
}

export function initBotControls(){
  els.startBtn?.addEventListener("click", async () => {
    closeDropdownPublic();
    try{
      // silently persist current selection before starting
      const chosen = getSelectedArray();
      if (chosen.length) { try { await saveSelection(chosen); } catch {} }
      await startBot();
      setStatus("Running");
    }catch{ setStatus("Unknown"); }
  });
  els.stopBtn?.addEventListener("click", async () => {
    closeDropdownPublic();
    try{
      await stopBot();
      setStatus("Stopped");
    }catch{ setStatus("Unknown"); }
  });

  // Save button (silent)
  els.saveBtn?.addEventListener("click", async ()=>{
    const chosen = getSelectedArray();
    els.saveBtn.disabled = true;
    try{ await saveSelection(chosen); }catch(e){ console.warn("Save failed:", e); }
    finally{ els.saveBtn.disabled = false; }
  });
}
