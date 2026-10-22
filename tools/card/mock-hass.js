// A stand-in for the frontend's `hass` object, built from a scenario. Status
// labels come from the integration's own English translations.
import { rxStatus } from "./scenarios.js";

const TRANSLATIONS = new URL("../../custom_components/xpon_onu_stick/translations/en.json", import.meta.url);
export const DEVICE_ID = "preview-stick";
const UNITS = {
  cpu_usage: "%",
  memory_usage: "%",
  temperature: "°C",
  voltage: "V",
  tx_power: "dBm",
  rx_power: "dBm",
  bias_current: "mA",
};
// Matches suggested_display_precision in sensor.py.
const PRECISION = { cpu_usage: 0, memory_usage: 0, temperature: 2, voltage: 3, tx_power: 2, rx_power: 2, bias_current: 2 };

export async function loadTranslations() {
  const response = await fetch(TRANSLATIONS, { cache: "no-store" });
  return (await response.json()).entity.sensor;
}

const slug = (text) => String(text).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");

/** A calm day on the link: a slow drift plus small polling noise, always the same. */
function historyRows(history, start, end) {
  let seed = 7;
  const noise = () => ((seed = (seed * 16807) % 2147483647) / 2147483647 - 0.5) * 0.05;
  const rows = [];
  for (let time = start; time <= end; time += 60000) {
    const hours = (time - start) / 3600000;
    const value = history.center + history.drift * Math.sin(hours / 3.8) + 0.03 * Math.sin(hours * 1.7) + noise();
    rows.push({ s: value.toFixed(6), lu: time / 1000 });
  }
  return rows;
}

export function createHass(scenario, translations, { historyFails = false } = {}) {
  const states = {};
  const entities = {};
  const name = scenario.values.device_name;
  const prefix = `sensor.${slug(name && name !== "unavailable" ? name : "xpon_onu_stick")}_`;
  const add = (key, state, attributes = {}) => {
    const entityId = `${prefix}${key}`;
    states[entityId] = {
      entity_id: entityId,
      state: String(state),
      attributes: UNITS[key] ? { unit_of_measurement: UNITS[key], ...attributes } : attributes,
      last_updated: new Date().toISOString(),
    };
    entities[entityId] = {
      entity_id: entityId,
      platform: "xpon_onu_stick",
      device_id: DEVICE_ID,
      translation_key: key,
      display_precision: PRECISION[key],
    };
  };
  for (const [key, value] of Object.entries(scenario.values)) add(key, value);
  for (const [key, [state, attributes]] of Object.entries(scenario.statuses)) add(key, state, attributes);

  const hasStick = Object.keys(states).length > 0;
  return {
    states,
    entities,
    devices: hasStick ? { [DEVICE_ID]: { id: DEVICE_ID, name: name === "unavailable" ? "AOT5222ZY" : name } } : {},
    locale: { language: "en" },
    language: "en",
    formatEntityState(stateObj) {
      const key = entities[stateObj.entity_id]?.translation_key;
      if (stateObj.state === "unavailable") return "Unavailable";
      if (stateObj.state === "unknown") return "Unknown";
      const label = translations[key]?.state?.[stateObj.state];
      if (label) return label;
      if (key in PRECISION) {
        const number = Number(stateObj.state).toFixed(PRECISION[key]);
        return UNITS[key] === "%" ? `${number}%` : `${number} ${UNITS[key]}`;
      }
      return stateObj.state;
    },
    async callWS(message) {
      if (message.type !== "history/history_during_period") throw new Error(`Unsupported: ${message.type}`);
      if (historyFails || !scenario.history) throw new Error("History is not available");
      const rows = historyRows(scenario.history, Date.parse(message.start_time), Date.parse(message.end_time));
      return { [message.entity_ids[0]]: rows };
    },
  };
}

/** Simulate the next poll: nudge the live readings and keep statuses consistent. */
export function nextPoll(hass) {
  const states = { ...hass.states };
  const keyOf = (entityId) => hass.entities[entityId]?.translation_key;
  const byKey = Object.fromEntries(Object.keys(states).map((entityId) => [keyOf(entityId), entityId]));
  const nudge = (key, spread, digits, minimum = -Infinity, maximum = Infinity) => {
    const entityId = byKey[key];
    const current = Number(states[entityId]?.state);
    if (!Number.isFinite(current)) return undefined;
    const value = Math.min(maximum, Math.max(minimum, current + (Math.random() - 0.5) * spread));
    states[entityId] = { ...states[entityId], state: value.toFixed(digits), last_updated: new Date().toISOString() };
    return value;
  };
  const rx = nudge("rx_power", 0.6, 6);
  nudge("tx_power", 0.1, 6);
  nudge("temperature", 0.6, 6);
  nudge("cpu_usage", 8, 0, 0, 100);
  if (rx !== undefined && byKey.rx_power_status) {
    const [state, attributes] = rxStatus(rx);
    states[byKey.rx_power_status] = { ...states[byKey.rx_power_status], state, attributes };
  }
  return { ...hass, states };
}
