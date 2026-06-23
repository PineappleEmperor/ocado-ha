"""The Ocado integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import DOMAIN
from .coordinator import OcadoConfigEntry, OcadoUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, config_entry: OcadoConfigEntry) -> bool:
    """Set up the Ocado integration from a config entry."""
    _LOGGER.debug("Setting up the Ocado integration")

    coordinator = OcadoUpdateCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()
    config_entry.runtime_data = coordinator

    await cleanup_old_device(hass)
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: OcadoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: OcadoConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow a device to be deleted from the UI."""
    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: OcadoConfigEntry) -> None:
    """Reload the integration when its options change."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def cleanup_old_device(hass: HomeAssistant) -> None:
    """Remove a legacy device left with a malformed identifier."""
    device_reg = dr.async_get(hass)
    device = device_reg.async_get_device(identifiers={(DOMAIN,)})  # type: ignore[arg-type]  # malformed 1-tuple identifier intentionally matches legacy device to clean up
    if device:
        _LOGGER.debug("Removing improper device %s", device.name)
        device_reg.async_remove_device(device.id)
