"""Test sensor for simple integration."""

import pytest
from unittest.mock import AsyncMock
from homeassistant.core import HomeAssistant
from pathlib import Path
import json
from datetime import datetime, timezone
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.ocado.const import OcadoOrder
from custom_components.ocado.coordinator import OcadoUpdateCoordinator

from homeassistant.setup import async_setup_component
from custom_components.ocado.const import DOMAIN


# async def test_async_setup(hass):
#     """Test the component gets setup."""
#     assert await async_setup_component(hass, DOMAIN, {}) is True


# @pytest.mark.asyncio
# async def test_coordinator_setup(hass: HomeAssistant, mock_config_entry, aioclient_mock):
#     # Set up the config entry
#     await hass.config_entries.async_setup(mock_config_entry.entry_id)
#     await hass.async_block_till_done()

#     # Access your coordinator (this depends on how your integration stores it)
#     coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]["coordinator"]

#     assert isinstance(coordinator, OcadoUpdateCoordinator)
#     expected_output = {
#         'message_ids': [b'1'],
#         'next': OcadoOrder(
#                 updated = datetime(2025, 5, 27, 15, 0, 0, tzinfo=timezone.utc),
#                 order_number = "1234567891",
#                 delivery_datetime = datetime(2025, 6, 22, 10, 0, 0),
#                 delivery_window_end = datetime(2025, 6, 22, 11, 0, 0),
#                 edit_datetime = datetime(2025, 6, 21, 17, 25, 0),
#                 estimated_total = "3.50",
#             )
#         }
#     assert vars(coordinator.data["next"]) == vars(expected_output["next"])
#     # _LOGGER.debug("Coordinator data is %s", coordinator.data)

# @pytest.mark.asyncio
# async def test_ocado_update_coordinator(hass, aioclient_mock):
#     """Test the OcadoUpdateCoordinator with mocked API responses."""
#     fixtures_path = Path(__file__).parent / "fixtures"
#     with open(fixtures_path / "none.json") as file:
#         data = json.load(file)    
#     # Mock the API endpoint for a successful response
#     mock_api_url = ""
#     aioclient_mock.get(
#         mock_api_url,
#         json=data,
#         status=200,
#     )

#     # Initialize the coordinator
#     coordinator = OcadoUpdateCoordinator(hass, mock_config_entry)
#     coordinator.api_key = "test_api_key"  # Ensure the API key is set
#     coordinator.session = hass.helpers.aiohttp_client.async_get_clientsession(hass)

#     # Perform the update
#     await coordinator.async_refresh()

#     # Assert the data was fetched correctly
#     assert coordinator.last_update_success
#     assert coordinator.data[""] == data[""] #