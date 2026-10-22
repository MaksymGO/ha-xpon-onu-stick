"""Serve the bundled card and register it as a persistent dashboard resource."""

import logging
from pathlib import Path
from urllib.parse import urlsplit

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import CARD_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)
_DATA_STATIC_PATH = f"{DOMAIN}_card_static_path"


async def async_register_card(hass: HomeAssistant, _component: str) -> None:
    """Use the dashboard loader instead of importing the card in the page header."""
    if hass.http is None:
        return
    if not hass.data.get(_DATA_STATIC_PATH):
        card = Path(__file__).parent / "frontend" / "xpon-onu-stick-card.js"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card), cache_headers=False)]
        )
        hass.data[_DATA_STATIC_PATH] = True

    integration = await async_get_integration(hass, DOMAIN)
    url = f"{CARD_URL}?v={integration.version}"
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None or not isinstance(lovelace.resources, ResourceStorageCollection):
        _LOGGER.warning(
            "Dashboard resources are managed in YAML. Add %s with type: module to your "
            "lovelace resources, then reload the browser page",
            url,
        )
        return

    resources = lovelace.resources
    await resources.async_get_info()
    existing = []
    for item in resources.async_items():
        parsed = urlsplit(item["url"])
        if not parsed.scheme and not parsed.netloc and parsed.path == CARD_URL:
            existing.append(item)
    if existing:
        resource = existing[0]
        if resource["url"] != url or resource["type"] != "module":
            await resources.async_update_item(resource["id"], {"url": url, "res_type": "module"})
        for duplicate in existing[1:]:
            await resources.async_delete_item(duplicate["id"])
    else:
        await resources.async_create_item({"url": url, "res_type": "module"})
