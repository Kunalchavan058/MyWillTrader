import { els } from "../util/dom.js";
import { fetchSettings, postSettings } from "../core/api.js";

export async function loadSettingsUI(){
  try{
    const d = await fetchSettings();
    if (els.afterHoursToggleHead) els.afterHoursToggleHead.checked = !!d.test_mode;
    if (els.capitalInput) els.capitalInput.value = d.capital_per_trade ?? "";
    if (els.intervalInput) els.intervalInput.value = d.interval_minutes ?? "";
    if (els.paperToggle) els.paperToggle.checked = !!d.paper_trading;
  }catch{}
}

async function saveSettingsUI(partial){
  const payload = {
    test_mode: !!els.afterHoursToggleHead?.checked,
    capital_per_trade: Number(els.capitalInput?.value || 0) || undefined,
    interval_minutes: Number(els.intervalInput?.value || 0) || undefined,
    paper_trading: !!els.paperToggle?.checked,
    ...partial
  };
  try { await postSettings(payload); } catch {}
}

export function initSettingsUI(){
  els.settingsSaveBtn?.addEventListener("click", async ()=>{ await saveSettingsUI({}); });
  els.afterHoursToggleHead?.addEventListener("change", async ()=>{ await saveSettingsUI({}); });
}
