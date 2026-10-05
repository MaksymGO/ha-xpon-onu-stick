// Drives preview.html in three modes (?mode=...):
//   debug (default)  interactive preview that reloads when card files change
//   shot             one card for a screenshot (?scenario=&theme=&width=)
//   test             runs ui-tests.js and shows the results
import { createHass, loadTranslations, nextPoll } from "./mock-hass.js";
import { SCENARIOS } from "./scenarios.js";

const CARD = "xpon-onu-stick-card";
const params = new URLSearchParams(location.search);
const app = document.getElementById("app");
const settle = () => new Promise((resolve) => setTimeout(resolve, 60));
const WATCHED = [
  "../../custom_components/xpon_onu_stick/frontend/xpon-onu-stick-card.js",
  "../../custom_components/xpon_onu_stick/translations/en.json",
  "preview.html",
  "preview.js",
  "mock-hass.js",
  "scenarios.js",
  "ha-stubs.js",
  "ui-tests.js",
];

function createCard(config, hass) {
  const card = document.createElement(CARD);
  card.setConfig({ type: `custom:${CARD}`, ...config });
  card.hass = hass;
  return card;
}

async function shot() {
  const translations = await loadTranslations();
  document.body.className = "shot";
  const stage = document.createElement("div");
  stage.id = "stage";
  stage.className = `surface theme-${params.get("theme") || "light"}`;
  stage.style.setProperty("--card-width", `${Number(params.get("width")) || 500}px`);
  const scenario = SCENARIOS[params.get("scenario") || "healthy"];
  stage.append(createCard({}, createHass(scenario, translations)));
  app.replaceChildren(stage);
  await settle();
  await document.fonts.ready;
}

async function runTests() {
  const { runCardTests } = await import("./ui-tests.js");
  const results = await runCardTests();
  const failed = results.filter((result) => !result.ok).length;
  const list = results
    .map(({ name, ok, error }) => `<li class="${ok ? "pass" : "fail"}">${ok ? "✓" : "✗"} ${name}${ok ? "" : ` — ${error}`}</li>`)
    .join("");
  app.innerHTML = `<div class="results"><strong>${results.length - failed} passed, ${failed} failed</strong><ul>${list}</ul></div>`;
  return results;
}

/** Reload the page when the card or the preview files change on disk. */
function watchFiles() {
  const stamps = new Map();
  setInterval(async () => {
    if (!document.getElementById("live")?.checked) return;
    for (const file of WATCHED) {
      try {
        const response = await fetch(file, { method: "HEAD", cache: "no-store" });
        const stamp = response.headers.get("last-modified");
        if (stamps.has(file) && stamps.get(file) !== stamp) location.reload();
        stamps.set(file, stamp);
      } catch {
        // The preview server stopped; keep the page as it is.
      }
    }
  }, 1000);
}

async function debug() {
  const translations = await loadTranslations();
  const state = {
    scenario: params.get("scenario") || "healthy",
    theme: params.get("theme") || "both",
    width: params.get("width") || "500",
    historyFails: params.get("historyFails") === "1",
    config: JSON.parse(params.get("config") || "{}"),
  };
  const scenarioOptions = Object.entries(SCENARIOS)
    .map(([key, scenario]) => `<option value="${key}">${scenario.label}</option>`)
    .join("");
  app.innerHTML = `
    <div class="toolbar">
      <strong>XPON ONU Stick card</strong>
      <label>Scenario <select id="scenario">${scenarioOptions}</select></label>
      <label>Theme <select id="theme"><option value="both">Light and dark</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
      <label>Width <select id="width"><option value="290">Narrow (290 px)</option><option value="400">Medium (400 px)</option><option value="500">Section (500 px)</option><option value="700">Wide (700 px)</option></select></label>
      <button id="poll" title="Nudge the live readings as if a new poll arrived">Next poll</button>
      <label><input type="checkbox" id="historyFails"> History error</label>
      <span class="spacer"></span>
      <label><input type="checkbox" id="live" checked> Live reload</label>
      <a href="?mode=test" target="_blank">Run UI tests</a>
    </div>
    <div class="layout">
      <div id="cards" class="layout" style="padding:0"></div>
      <div class="side">
        <div class="box"><h2>Card editor</h2><div id="editor"></div></div>
        <div class="box"><h2>YAML</h2><pre id="yaml"></pre></div>
        <div class="box"><h2>Events</h2><pre id="log"></pre></div>
      </div>
    </div>`;

  const log = (message) => {
    const element = document.getElementById("log");
    element.textContent = `${new Date().toLocaleTimeString()} ${message}\n${element.textContent}`;
  };
  const yaml = (config) =>
    Object.entries({ type: `custom:${CARD}`, ...config })
      .map(([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
      .join("\n");
  let hass;
  let cards = [];

  const saveUrl = () => {
    const query = new URLSearchParams({ scenario: state.scenario, theme: state.theme, width: state.width });
    if (state.historyFails) query.set("historyFails", "1");
    if (Object.keys(state.config).length) query.set("config", JSON.stringify(state.config));
    history.replaceState(null, "", `?${query}`);
  };

  const renderCards = () => {
    hass = createHass(SCENARIOS[state.scenario], translations, { historyFails: state.historyFails });
    const themes = state.theme === "both" ? ["light", "dark"] : [state.theme];
    cards = themes.map(() => createCard(state.config, hass));
    document.getElementById("cards").replaceChildren(
      ...themes.map((theme, index) => {
        const panel = document.createElement("div");
        panel.className = `panel surface theme-${theme}`;
        panel.style.setProperty("--card-width", `${state.width}px`);
        panel.innerHTML = `<h2>${theme}</h2>`;
        panel.append(cards[index]);
        cards[index].addEventListener("hass-more-info", (event) => log(`more-info → ${event.detail.entityId}`));
        return panel;
      }),
    );
    document.getElementById("yaml").textContent = yaml(state.config);
    saveUrl();
  };

  const renderEditor = () => {
    const editor = customElements.get(CARD).getConfigElement();
    editor.addEventListener("config-changed", (event) => {
      const { type, ...config } = event.detail.config;
      state.config = config;
      log(`config-changed → ${JSON.stringify(event.detail.config)}`);
      editor.setConfig(event.detail.config);
      renderCards();
    });
    editor.hass = createHass(SCENARIOS[state.scenario], translations);
    editor.setConfig({ type: `custom:${CARD}`, ...state.config });
    document.getElementById("editor").replaceChildren(editor);
  };

  for (const key of ["scenario", "theme", "width"]) {
    const select = document.getElementById(key);
    select.value = state[key];
    select.addEventListener("change", () => {
      state[key] = select.value;
      renderCards();
      if (key === "scenario") renderEditor();
    });
  }
  const historyFails = document.getElementById("historyFails");
  historyFails.checked = state.historyFails;
  historyFails.addEventListener("change", () => {
    state.historyFails = historyFails.checked;
    renderCards();
  });
  document.getElementById("poll").addEventListener("click", () => {
    hass = nextPoll(hass);
    for (const card of cards) card.hass = hass;
    log("poll → new readings");
  });

  renderCards();
  renderEditor();
  watchFiles();
}

const mode = params.get("mode") || "debug";
window.cardPreviewReady = mode === "shot" ? shot() : mode === "test" ? runTests() : debug();
window.cardTestResults = mode === "test" ? window.cardPreviewReady : undefined;
