"""The Ocado integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import UpdateFailed

from homeassistant.helpers import config_validation as cv, device_registry as dr
# , device_registry as dr

from .const import DOMAIN
from .coordinator import OcadoUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR
]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config_entry: dict) -> bool:
    """Set up the Ocado component."""
    _LOGGER.debug("async_setup called")
    try:
        hass.data[DOMAIN] = {}
        _LOGGER.debug("hass.data[%s] initialized", DOMAIN)
    except Exception as error:
        _LOGGER.exception("Unexpected error in async_setup: %s", error)
        return False
    _LOGGER.info("[%s] async_setup completed without errors.", DOMAIN)
    return True

        # async def handle_manual_refresh(call):
        #     """Refresh all Ocado sensors for a given config entry."""
        #     _LOGGER.debug("manual_refresh service called with data: %s", call.data)
        #     entry_id = call.data.get("entry_id")

        #     if not entry_id:
        #         _LOGGER.error("[Ocado-ha] No entry_id was passed to ocado-ha.manual_refresh service.")
        #         return

        #     if entry_id not in hass.data[DOMAIN]:
        #         _LOGGER.error("[Ocado-ha] No config entry found for entry_id: %s", entry_id)
        #         return

        #     coordinator = hass.data[DOMAIN][entry_id].get("coordinator")
        #     if not coordinator:
        #         _LOGGER.error("[Ocado-ha] Coordinator is missing for entry_id: %s",entry_id)
        #         return

        #     _LOGGER.debug("[Ocado-ha] Requesting a manual refresh via coordinator")
        #     await coordinator.async_request_refresh()
        #     _LOGGER.debug("[Ocado-ha] Manual refresh completed")

        # # Register a service named `ocado_ha.manual_refresh`
        # _LOGGER.debug("[Ocado-ha] Registering manual_refresh service")
        # hass.services.async_register(DOMAIN, "manual_refresh", handle_manual_refresh)
        # _LOGGER.debug("[Ocado-ha] manual_refresh service registered successfully")


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up the Ocado integration."""
    _LOGGER.info("Setting up the Ocado integration")

    # Check if the entry is already set up
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        raise ValueError(
            f"Config entry {config_entry.title} ({config_entry.entry_id}) for {DOMAIN} has already been setup!"
        )

    try:
        # Setup the coordinator and perform the first refresh
        coordinator = OcadoUpdateCoordinator(hass, config_entry)
        _LOGGER.debug("OcadoUpdateCoordinator initialised.")
        await coordinator.async_config_entry_first_refresh()

        if not coordinator.data:
            raise ConfigEntryNotReady
        _LOGGER.info(
            f"Initial data fetched successfully for entry_id={config_entry.entry_id}"
        )

        # Store the coordinator
        _LOGGER.debug("Storing coordinator")
        hass.data.setdefault(DOMAIN,{})[config_entry.entry_id] = {"coordinator": coordinator}

        _LOGGER.debug(
            f"Coordinator stored in hass.data under entry_id={config_entry.entry_id}"
        )

        # Forward the setup to all platforms
        if "platforms" not in hass.data[DOMAIN][config_entry.entry_id]:
            _LOGGER.debug(f"Forwarding setup to platforms: {PLATFORMS}")
            await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
            hass.data[DOMAIN][config_entry.entry_id]["platforms"] = PLATFORMS
        _LOGGER.info(
            f"async_setup_entry finished for entry_id={config_entry.entry_id}"
        )
        _LOGGER.debug("Cleaning up old devices.")
        await cleanup_old_device(hass)
        _LOGGER.debug("Completed cleaning up old devices.")
        # config_entry.runtime_data = coordinator
        # config_entry.async_on_unload(config_entry.add_update_listener(async_update_entry))
        return True
    
    except UpdateFailed as error:
        _LOGGER.error("Unable to fetch initial data: %s", error)
        raise ConfigEntryNotReady from error


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle config options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)

# async def async_remove_config_entry_device(
#     hass: HomeAssistant, config_entry: OcadoConfigEntry, device_entry: DeviceEntry
# ) -> bool:
#     """Delete device if selected from UI."""
#     return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # # Unload services
    # for service in hass.services.async_services_for_domain(DOMAIN):
    #     hass.services.async_remove(DOMAIN, service)

    # Unload platforms and return result
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

async def async_update_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Reload Ocado component when options changed."""
    await hass.config_entries.async_reload(config_entry.entry_id)
    
async def cleanup_old_device(hass: HomeAssistant) -> None:
    """Cleanup device without proper device identifier."""
    device_reg = dr.async_get(hass)
    _LOGGER.debug("Device reg is %s", device_reg)
    device = device_reg.async_get_device(identifiers={(DOMAIN,)})
    _LOGGER.debug("Device is %s", device)
    if device:
        _LOGGER.debug("Removing improper device %s", device.name)
        device_reg.async_remove_device(device.id)
