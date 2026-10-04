"""Verify the dashboard card is served and can find every sensor."""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_HOST
from homeassistant.helpers import entity_registry as er

from custom_components.xpon_onu_stick import async_setup
from custom_components.xpon_onu_stick.const import CARD_URL, DOMAIN
from custom_components.xpon_onu_stick.sensor import SENSORS, STATUS_SENSORS

CARD = (
    Path(__file__).parents[1] / "custom_components" / DOMAIN / "frontend" / "xpon-onu-stick-card.js"
)


async def test_card_is_served_and_loaded_when_the_frontend_runs(hass):
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    hass.config.components.add("frontend")
    with patch("homeassistant.components.frontend.add_extra_js_url") as add_js:
        assert await async_setup(hass, {})

    (paths,), _ = hass.http.async_register_static_paths.call_args
    assert [(path.url_path, Path(path.path)) for path in paths] == [(CARD_URL, CARD)]
    assert CARD.is_file()
    add_js.assert_called_once()
    assert add_js.call_args.args[1].startswith(f"{CARD_URL}?v=")


async def test_card_is_skipped_without_a_frontend(hass):
    assert hass.http is None
    with patch("homeassistant.components.frontend.add_extra_js_url") as add_js:
        assert await async_setup(hass, {})
    add_js.assert_not_called()


def test_card_uses_the_integration_domain():
    assert re.search(rf'const DOMAIN = "{DOMAIN}";', CARD.read_text())


async def test_every_sensor_has_the_translation_key_the_card_uses(hass, onu_server):
    host, _, _ = onu_server
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={CONF_HOST: host}
    )
    await hass.async_block_till_done()

    entries = er.async_entries_for_config_entry(er.async_get(hass), result["result"].entry_id)
    keys = {description.key for description in SENSORS + STATUS_SENSORS}
    assert {entry.translation_key for entry in entries} == keys
    assert len(entries) == len(keys)
