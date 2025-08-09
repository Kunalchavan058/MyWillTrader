import { els } from "../util/dom.js";

export function renderState(snap){
  if (els.stateTs) els.stateTs.textContent = `Last update: ${new Date(snap.ts).toLocaleString()}`;
  const rows = snap.rows || [];
  els.stateTableBody.innerHTML = rows.map(r=>{
    const pnl = r.pnl_pct==null ? "-" : (r.pnl_pct>=0? `+${r.pnl_pct.toFixed(2)}` : r.pnl_pct.toFixed(2));
    const entry = r.entry==null? "-" : Number(r.entry).toFixed(2);
    const last  = r.last ==null? "-" : Number(r.last ).toFixed(2);
    return `<tr><td>${r.ticker}</td><td>${r.state}</td><td>${r.qty||0}</td><td>${entry}</td><td>${last}</td><td>${pnl}</td></tr>`;
  }).join("");
}
