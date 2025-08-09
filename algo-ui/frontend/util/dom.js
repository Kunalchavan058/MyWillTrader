// Centralize element lookups
export const els = {
  listEl: document.getElementById("list"),
  searchEl: document.getElementById("search"),
  // addBtn removed (we no longer support manual add)
  saveBtn: document.getElementById("save"),
  selectedListEl: document.getElementById("selectedList"),
  watchlistCard: document.getElementById("watchlistCard"),

  startBtn: document.getElementById("startBot"),
  stopBtn: document.getElementById("stopBot"),

  afterHoursToggleHead: document.getElementById("afterHoursToggleHead"),

  stateTableBody: document.querySelector("#stateTable tbody"),
  stateTs: document.getElementById("stateTs"),
  countdownEl: document.getElementById("countdown"),

  themeToggleBtn: document.getElementById("themeToggle"),
  settingsSaveBtn: document.getElementById("settingsSaveBtn"),
  capitalInput: document.getElementById("capitalInput"),
  intervalInput: document.getElementById("intervalInput"),
  paperToggle: document.getElementById("paperToggle"),
};
