// Fetch wrappers
async function jsonFetch(url, opts={}) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(await res.text().catch(()=>res.statusText));
  return res.json();
}

export async function fetchTickers() {
  const data = await jsonFetch("/api/tickers");
  return data.symbols || [];
}

export async function saveSelection(symbols) {
  return jsonFetch("/api/selection", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ symbols }),
  });
}

export async function fetchSettings() {
  try { return await jsonFetch("/api/settings"); }
  catch { return {}; }
}

export async function postSettings(payload) {
  return jsonFetch("/api/settings", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload),
  });
}

export async function fetchBotStatus() {
  return jsonFetch("/api/bot/status");
}
export async function startBot() {
  return jsonFetch("/api/bot/start", { method:"POST" });
}
export async function stopBot() {
  return jsonFetch("/api/bot/stop", { method:"POST" });
}
