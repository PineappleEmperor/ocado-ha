# """Provide info to system health."""

# import os
# from typing import Any

# from homeassistant.components import system_health
# from homeassistant.config_entries import ConfigEntry
# from homeassistant.core import HomeAssistant, callback

# from .const import (
#     # DOMAIN,
#     CONF_IMAP_SERVER,
# )

# @callback
# def async_register(hass: HomeAssistant, register: system_health.SystemHealthRegistration) -> None:
#     """Register system health callbacks."""
#     register.async_register_info(system_health_info)

# async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
#     """Get info for the info page."""
#     # config_entry: ConfigEntry = hass.config_entries.async_entries(DOMAIN)[0]
#     # quota_info = await config_entry.runtime_data.async_get_quota_info()

#     return {
#         # "consumed_requests": quota_info.consumed_requests,
#         # "remaining_requests": quota_info.requests_remaining,
#         # checking the url can take a while, so set the coroutine in the info dict
#         "can_reach_server": system_health.async_check_can_reach_url(hass, CONF_IMAP_SERVER),
#     }