import { els } from "./dom.js";

let countdownTimer = null;
let countdownRemaining = null;

function renderCountdown(){
  const s = Math.max(0, Math.floor(countdownRemaining||0));
  const m = Math.floor(s/60), r=s%60;
  if (els.countdownEl) els.countdownEl.textContent = `⏳ ${String(m).padStart(2,"0")}:${String(r).padStart(2,"0")}`;
}

export function startCountdown(sec){
  if(countdownTimer) clearInterval(countdownTimer);
  countdownRemaining = Number(sec)||0; renderCountdown();
  countdownTimer = setInterval(()=>{ 
    if(countdownRemaining>0){ countdownRemaining--; renderCountdown(); }
    else { clearInterval(countdownTimer); countdownTimer=null; }
  },1000);
}
