"""The Ocado integration."""

import logging
from typing import Any, Callable

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import DOMAIN
from .coordinator import OcadoUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR
]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

type OcadoConfigEntry = ConfigEntry[RuntimeData]

@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: DataUpdateCoordinator
    cancel_update_listener: Callable


async def async_setup_entry(hass: HomeAssistant, config_entry: OcadoConfigEntry) -> bool:
    """Set up the Ocado integration."""
    _LOGGER.info("Setting up the Ocado integration")

    # Check if the entry is already set up
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        raise ValueError(
            f"Config entry {config_entry.title} ({config_entry.entry_id}) for {DOMAIN} has already been setup!"
        )

    # Setup the coordinator
    coordinator = OcadoUpdateCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.data:
        raise ConfigEntryNotReady

    cancel_update_listener = config_entry.async_on_unload(
        config_entry.add_update_listener(_async_update_listener)
    )

    config_entry.runtime_data = RuntimeData(coordinator, cancel_update_listener)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Store integration data in hass.data
    hass.data[DOMAIN] = {}

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: OcadoConfigEntry):
    """Handle config options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)

# async def async_remove_config_entry_device(
#     hass: HomeAssistant, config_entry: OcadoConfigEntry, device_entry: DeviceEntry
# ) -> bool:
#     """Delete device if selected from UI."""
#     return True

async def async_unload_entry(hass: HomeAssistant, config_entry: OcadoConfigEntry) -> bool:
    """Unload a config entry."""

    # # Unload services
    # for service in hass.services.async_services_for_domain(DOMAIN):
    #     hass.services.async_remove(DOMAIN, service)

    # Unload platforms and return result
    # return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        platforms = hass.data[DOMAIN][config_entry.entry_id].get("platforms", [])
        unload_ok = await hass.config_entries.async_unload_platforms(config_entry, platforms)

        # Clean up resources
        if unload_ok:
            hass.data[DOMAIN].pop(config_entry.entry_id)
            # If no entries remain, clean up DOMAIN
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN)

        return unload_ok

    return False

async def async_update_entry(hass: HomeAssistant, config_entry: OcadoConfigEntry):
    """Reload Ocado component when options changed."""
    await hass.config_entries.async_reload(config_entry.entry_id)