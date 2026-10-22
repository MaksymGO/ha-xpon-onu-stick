# Dashboard card

Edit a dashboard, select **Add card**, and search for **XPON ONU Stick**. No dashboard resource is needed.

```yaml
type: custom:xpon-onu-stick-card
```

## Options

| Option | Default | Use |
| --- | --- | --- |
| `device_id` | First stick found | Choose a stick when you have several. |
| `title` | Device name | Set the card title. |
| `show_history` | `true` | Show the 24-hour Rx power trend. |
| `show_system` | `true` | Show CPU and memory usage. |
| `show_details` | `true` | Show ONU and network details. |
| `hide_mac` | `false` | Hide the MAC address. |

Select a reading to open its details and history. The card uses Home Assistant data and does not contact the stick. Reload the browser page if the card is missing after an update.

See the [light and dark previews](screenshots.md#dashboard-card).

## Built-in cards

Paste [examples/dashboard.yaml](../examples/dashboard.yaml) into a **Manual** card. Replace the sample `sensor.aot5222zy_*` entity IDs with those shown for your stick.
