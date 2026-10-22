// Sample readings for the card preview, UI tests, and README screenshots.

export const RX_LIMITS = { minimum: -27, maximum: -8, warning_margin: 2 };

/** Classify Rx power the way the integration does with its default limits. */
export function rxStatus(reading) {
  const { minimum, maximum, warning_margin: margin } = RX_LIMITS;
  let state = "good";
  if (reading < minimum) state = "low";
  else if (reading > maximum) state = "high";
  else if (reading <= minimum + margin) state = "weak";
  else if (reading >= maximum - margin) state = "strong";
  const descriptions = {
    good: "The reading is within the configured normal range.",
    weak: "Receive power is close to the configured minimum.",
    strong: "Receive power is close to the configured maximum.",
    low: "The reading is below the configured minimum.",
    high: "The reading has reached or exceeded the configured upper limit.",
  };
  return [
    state,
    {
      reading,
      ...RX_LIMITS,
      lower_margin_db: Number((reading - minimum).toFixed(6)),
      upper_margin_db: Number((maximum - reading).toFixed(6)),
      description: descriptions[state],
    },
  ];
}

const HEALTHY_VALUES = {
  device_name: "AOT5222ZY",
  uptime: "3 days, 21:22",
  firmware_version: "V1.0-220923",
  cpu_usage: 3,
  memory_usage: 50,
  ip_address: "192.168.1.1",
  subnet_mask: "255.255.255.0",
  mac_address: "020000000001",
  temperature: 41.2,
  voltage: 3.2561,
  tx_power: 2.060723,
  rx_power: -21.84,
  bias_current: 11.4,
  onu_state: "O5",
  onu_id: 0,
  loid_status: "Initial Status",
};
const CONNECTED = [
  "connected",
  { onu_state: "O5", description: "The GPON optical connection is established with the provider." },
];
const HEALTHY_STATUSES = {
  rx_power_status: rxStatus(HEALTHY_VALUES.rx_power),
  tx_power_status: ["good", {}],
  temperature_status: ["good", {}],
  voltage_status: ["good", {}],
  bias_current_status: ["limits_not_set", {}],
  onu_registration_status: CONNECTED,
};
const READINGS = Object.keys(HEALTHY_VALUES);
const STATUSES = Object.keys(HEALTHY_STATUSES);
const unavailable = (keys, value) => Object.fromEntries(keys.map((key) => [key, value]));

export const SCENARIOS = {
  healthy: {
    label: "Healthy link (README images)",
    values: HEALTHY_VALUES,
    statuses: HEALTHY_STATUSES,
    history: { center: -21.86, drift: 0.07 },
  },
  weak: {
    label: "Weak signal (the tested stick's readings)",
    values: { ...HEALTHY_VALUES, cpu_usage: 0, temperature: 39.308594, rx_power: -26.382721 },
    statuses: { ...HEALTHY_STATUSES, rx_power_status: rxStatus(-26.382721) },
    history: { center: -26.36, drift: 0.12 },
  },
  problem: {
    label: "Problems: no registration, readings out of range",
    values: {
      ...HEALTHY_VALUES,
      device_name: "ODI Stick",
      uptime: "0:07",
      cpu_usage: 82,
      memory_usage: 93,
      temperature: 71.2,
      voltage: 3.05,
      tx_power: 0.2,
      rx_power: -28.4,
      onu_state: "O2",
      onu_id: 255,
      loid_status: "Wrong",
    },
    statuses: {
      rx_power_status: rxStatus(-28.4),
      tx_power_status: ["low", {}],
      temperature_status: ["high", {}],
      voltage_status: ["low", {}],
      bias_current_status: ["good", {}],
      onu_registration_status: [
        "standby",
        { onu_state: "O2", description: "The ONU is receiving the provider's signal and waiting for registration parameters." },
      ],
    },
    history: { center: -28.2, drift: 0.3 },
  },
  unavailable: {
    label: "Stick unreachable",
    values: unavailable(READINGS, "unavailable"),
    statuses: unavailable(STATUSES, ["unavailable", {}]),
    history: null,
  },
  empty: {
    label: "No stick configured",
    values: {},
    statuses: {},
    history: null,
  },
};
