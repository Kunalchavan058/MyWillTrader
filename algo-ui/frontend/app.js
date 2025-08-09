// ---------- Element refs ----------
const listEl = document.getElementById("list");
const searchEl = document.getElementById("search");
const addBtn   = document.getElementById("addBtn");
const saveBtn  = document.getElementById("save");
const selectedListEl = document.getElementById("selectedList");
const watchlistCard  = document.getElementById("watchlistCard");

const startBtn = document.getElementById("startBot");
const stopBtn  = document.getElementById("stopBot");

const afterHoursToggleHead = document.getElementById("afterHoursToggleHead"); // maps to test_mode

const stateTableBody = document.querySelector("#stateTable tbody");
const stateTs = document.getElementById("stateTs");
const countdownEl = document.getElementById("countdown");

const themeToggleBtn = document.getElementById("themeToggle");
const settingsSaveBtn = document.getElementById("settingsSaveBtn");
const capitalInput = document.getElementById("capitalInput");
const intervalInput = document.getElementById("intervalInput");
const paperToggle = document.getElementById("paperToggle");

// ---------- Theme ----------
(() => {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  themeToggleBtn.textContent = saved === "dark" ? "☀️" : "🌙";
  themeToggleBtn.addEventListener("click", () => {
    const t = document.documentElement.getAttribute("data-theme");
    const next = t === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    themeToggleBtn.textContent = next === "dark" ? "☀️" : "🌙";
    localStorage.setItem("theme", next);
  });
})();

// ---------- State ----------
let symbols = [];
let filtered = [];
let selected = new Set();

// ---------- Dropdown helpers ----------
function openDropdown(){
  const cardRect = watchlistCard.getBoundingClientRect();
  const inputRect = searchEl.getBoundingClientRect();
  listEl.style.left = (inputRect.left - cardRect.left) + "px";
  listEl.style.top  = (inputRect.bottom - cardRect.top + 6) + "px";
  listEl.style.width = inputRect.width + "px";
  listEl.classList.add("open");
}
function closeDropdown(){ listEl.classList.remove("open"); }
function renderDropdown(list){
  const items = list.map(sym => `<div class="row" data-sym="${sym}" role="option"><span class="symbol">${sym}</span></div>`).join("");
  listEl.innerHTML = items || `<div class="row" aria-disabled="true">No matches</div>`;
}
document.addEventListener("click",(e)=>{ if(!watchlistCard.contains(e.target)) closeDropdown(); });

// ---------- Selected rows ----------
function renderSelected(){
  const arr = Array.from(selected).sort();
  selectedListEl.innerHTML = arr.map(sym => `
    <div class="selected-item" data-sym="${sym}">
      <span class="dot"></span>
      <span class="ticker">${sym}</span>
      <button type="button" class="btn outline" data-remove="${sym}" style="margin-left:auto">Remove</button>
    </div>
  `).join("");
}
selectedListEl.addEventListener("click",(e)=>{
  const btn = e.target.closest("button[data-remove]");
  if(!btn) return;
  selected.delete(btn.dataset.remove);
  renderSelected();
});

// ---------- Load tickers ----------
async function loadTickers(){
  try{
    const res = await fetch("/api/tickers");
    if(!res.ok) throw new Error(await res.text());
    const data = await res.json();
    symbols = (data.symbols || []).map(String);
    filtered = symbols.slice();
  }catch{
    listEl.innerHTML = `<div class="row">Failed to load tickers</div>`;
  }
}

// ---------- Search / Add ----------
searchEl.addEventListener("focus", () => {
  renderDropdown(symbols.slice(0,50));
  openDropdown();
});
searchEl.addEventListener("input", () => {
  const q = searchEl.value.trim().toLowerCase();
  filtered = q ? symbols.filter(s=>s.toLowerCase().includes(q)) : symbols.slice();
  const list = filtered.filter(s => !selected.has(s));
  renderDropdown(list.slice(0,200));
  openDropdown();
});
listEl.addEventListener("click",(e)=>{
  const row = e.target.closest(".row[data-sym]");
  if(!row) return;
  const sym = row.dataset.sym;
  selected.add(sym);
  renderSelected();
  searchEl.value = "";
  closeDropdown();
});
addBtn.addEventListener("click", ()=>{
  const q = searchEl.value.trim().toUpperCase();
  if(!q) return;
  const sym = symbols.includes(q) ? q : (symbols.find(s=>s.startsWith(q)) || filtered[0]);
  if(sym){ selected.add(sym); renderSelected(); searchEl.value=""; closeDropdown(); }
});

// ---------- Save selection (silent) ----------
saveBtn.addEventListener("click", async ()=>{
  const chosen = Array.from(selected);
  saveBtn.disabled = true;
  try{
    const res = await fetch("/api/selection",{
      method:"POST", headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ symbols: chosen })
    });
    if(!res.ok) throw new Error(await res.text());
    // intentionally no UI message
  }catch(err){
    console.warn("Save failed:", err);
  }finally{
    saveBtn.disabled = false;
  }
});

// ---------- Settings (paper + off-hours in header) ----------
async function loadSettings(){
  try{
    const res = await fetch("/api/settings");
    const d = await res.json();
    afterHoursToggleHead.checked = !!d.test_mode; // single source of truth
    capitalInput && (capitalInput.value = d.capital_per_trade ?? "");
    intervalInput && (intervalInput.value = d.interval_minutes ?? "");
    paperToggle && (paperToggle.checked = !!d.paper_trading);
  }catch{}
}
async function saveSettings(partial){
  const payload = {
    test_mode: !!afterHoursToggleHead.checked,
    capital_per_trade: Number(capitalInput?.value || 0) || undefined,
    interval_minutes: Number(intervalInput?.value || 0) || undefined,
    paper_trading: !!paperToggle?.checked,
    ...partial
  };
  const res = await fetch("/api/settings",{
    method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify(payload)
  });
  return res.json();
}
settingsSaveBtn.addEventListener("click", async ()=>{ try{ await saveSettings({}); }catch{} });
afterHoursToggleHead.addEventListener("change", async ()=>{ try{ await saveSettings({}); }catch{} });

// ---------- Start/Stop button states ----------
function setStatus(stateText){
  const running = String(stateText).toLowerCase().includes("run");
  startBtn.classList.toggle("is-on", running);
  startBtn.querySelector(".lbl").textContent = running ? "Running" : "Start";
  stopBtn.classList.toggle("running", running);
  stopBtn.querySelector(".lbl").textContent = running ? "Stop" : "Stopped";
}
async function refreshStatus(){
  try{
    const res = await fetch("/api/bot/status");
    const data = await res.json();
    setStatus(data.running ? "Running" : "Stopped");
    afterHoursToggleHead.checked = !!data.test_mode;
  }catch{ setStatus("Unknown"); }
}
function safeCloseDropdown(){ closeDropdown(); }

startBtn.addEventListener("click", async () => {
  safeCloseDropdown();
  try{
    const res = await fetch("/api/bot/start",{method:"POST"});
    if(!res.ok){ setStatus("Unknown"); return; }
    await res.json();
    setStatus("Running");
  }catch{ setStatus("Unknown"); }
});
stopBtn.addEventListener("click", async () => {
  safeCloseDropdown();
  try{
    const res = await fetch("/api/bot/stop",{method:"POST"});
    if(!res.ok){ return; }
    await res.json();
    setStatus("Stopped");
  }catch{ setStatus("Unknown"); }
});

// ---------- Countdown + WS ----------
let ws, countdownTimer=null, countdownRemaining=null;
function startCountdown(sec){
  if(countdownTimer) clearInterval(countdownTimer);
  countdownRemaining = Number(sec)||0; renderCountdown();
  countdownTimer = setInterval(()=>{ 
    if(countdownRemaining>0){ countdownRemaining--; renderCountdown(); }
    else { clearInterval(countdownTimer); countdownTimer=null; }
  },1000);
}
function renderCountdown(){
  const s = Math.max(0, Math.floor(countdownRemaining||0));
  const m = Math.floor(s/60), r=s%60;
  countdownEl.textContent = `⏳ ${String(m).padStart(2,"0")}:${String(r).padStart(2,"0")}`;
}
function connectWS(){
  const proto = location.protocol==="https:"?"wss":"ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (e)=>{
    const t = e.data;
    const m = /Time to next\s+(\d+)-min candle:\s+(\d+)s/i.exec(t);
    if(m && m[2]) startCountdown(parseInt(m[2],10));
    try{ const obj = JSON.parse(t); if(obj && obj.type==="state"){ renderState(obj); return; } }catch{}
  };
  ws.onclose = ()=> setTimeout(connectWS,2000);
}
function renderState(snap){
  stateTs.textContent = `Last update: ${new Date(snap.ts).toLocaleString()}`;
  const rows = snap.rows || [];
  stateTableBody.innerHTML = rows.map(r=>{
    const pnl = r.pnl_pct==null ? "-" : (r.pnl_pct>=0? `+${r.pnl_pct.toFixed(2)}` : r.pnl_pct.toFixed(2));
    const entry = r.entry==null? "-" : Number(r.entry).toFixed(2);
    const last  = r.last ==null? "-" : Number(r.last ).toFixed(2);
    return `<tr><td>${r.ticker}</td><td>${r.state}</td><td>${r.qty||0}</td><td>${entry}</td><td>${last}</td><td>${pnl}</td></tr>`;
  }).join("");
}

// ---------- Init ----------
(async () => {
  await loadTickers();
  await loadSettings();
  await refreshStatus();
  connectWS();
})();
