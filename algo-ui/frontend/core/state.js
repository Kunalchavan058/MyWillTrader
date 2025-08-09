// App state + lightweight event bus
const bus = new EventTarget();

let symbols = [];
let filtered = [];
const selected = new Set();

export function setSymbols(list) {
  symbols = (list || []).map(String);
  filtered = symbols.slice();
  bus.dispatchEvent(new Event("symbols:updated"));
}
export function getSymbols() { return symbols.slice(); }
export function setFiltered(list) { filtered = list.slice(); }
export function getFiltered() { return filtered.slice(); }

export function addSelected(sym) {
  if (!sym) return;
  selected.add(sym);
  bus.dispatchEvent(new Event("selected:changed"));
}
export function removeSelected(sym) {
  selected.delete(sym);
  bus.dispatchEvent(new Event("selected:changed"));
}
export function getSelectedArray() {
  return Array.from(selected).sort();
}

export function on(type, handler) { bus.addEventListener(type, handler); }
export function off(type, handler) { bus.removeEventListener(type, handler); }
