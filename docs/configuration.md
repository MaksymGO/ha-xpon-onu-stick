# Configure XPON ONU Stick

## Before you start

- [Install the integration](installation.md) on Home Assistant **2026.9.0 or newer**.
- Make sure Home Assistant can reach the ONU's web interface.

## 1. Add the integration

1. Open **Settings → Devices & services → Add integration**.
2. Select **XPON ONU Stick**.
3. Enter the ONU's hostname, IP address, or base URL without a page path.
4. Enter its username and password. Leave both blank if login is not required.
5. Select **Submit**.

## 2. Check the readings

Open the device to see **22 entities**. Measurements appear under **Sensors** and device details under **Diagnostic**. See the [screenshots](screenshots.md).

## 3. Open the options

Open **Settings → Devices & services → XPON ONU Stick** and select the settings gear. Choose **Refresh interval** or **Status limits**.

## 4. Set the refresh interval

Enter **10 to 3600 seconds** and select **Submit**. The default is **30 seconds**.

<img src="screenshots/refresh-interval.png" alt="Refresh interval form" width="560">

## 5. Adjust the status limits

Use your module's specifications. Each maximum must exceed its minimum. For bias current, enter both limits or leave both blank.

See [default status limits](sensors.md#default-status-limits), then select **Submit** to save.

<img src="screenshots/status-limits.png" alt="Status limits form" width="440">

## 6. Change the address or login

Open the entry's menu and select **Reconfigure**. Enter the new address and credentials, including the password when login is required.

Changing the address preserves entities for the same stick. Add a different stick separately.

## 7. Add a dashboard

Select **Add card → XPON ONU Stick** in a dashboard. See [card options](dashboard.md), or use the [built-in card example](../examples/dashboard.yaml).

## Troubleshooting

- **Integration missing:** check installation and restart Home Assistant.
- **Connection or login fails:** check the address, network access, and credentials.
- **All sensors unavailable:** check both status pages and the [device identity](behavior.md#device-identity).
- **Reading unknown:** check its `parse_error` attribute and **Settings → System → Logs**. Other valid readings keep updating.
- **Card missing:** reload the browser page after updating the integration.

Use the [live check](development.md#test-the-real-stick) to read the stick directly.
