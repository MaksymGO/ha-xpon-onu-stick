# Connection and read-only behavior

The integration reads the stick's web interface, independently of the router or switch hosting it.

## Polling

All sensors share two requests every **30 seconds**. Set an interval from **10 to 3600 seconds** in [configuration](configuration.md#4-set-the-refresh-interval).

## Requests

- `GET /status.asp` for device readings.
- `GET /status_pon.asp` for PON readings.
- When login is needed, `GET /admin/login.asp` and `POST /boaform/admin/formLogin`.

HTTP Basic authentication is also supported. The integration does not change device settings or submit Refresh forms.

## Device identity

The MAC address identifies the stick. Changing its IP preserves existing entities. A different MAC requires a separate integration.

The device name and model come from the firmware's Device Name field, which may contain a cloned ONT name.

## Missing or invalid readings

- Empty or `N/A` values show as unknown.
- A bad field, such as `-inf dBm`, affects only that reading and its related status.
- The sensor includes a `parse_error` attribute. Details appear in **Settings → System → Logs**.
- Unchanged errors are not logged on every poll. Readings recover automatically.
- Connection, authentication, page, or MAC identity failures make all sensors unavailable.
