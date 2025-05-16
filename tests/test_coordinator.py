"""Test sensor for simple integration."""

# import pytest
# from unittest.mock import AsyncMock
# from pathlib import Path
# import json
# from datetime import datetime
# from custom_components.ocado.coordinator import OcadoUpdateCoordinator

from homeassistant.setup import async_setup_component
from custom_components.ocado.const import DOMAIN


async def test_async_setup(hass):
    """Test the component gets setup."""
    assert await async_setup_component(hass, DOMAIN, {}) is True


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

#     # Mock ConfigEntry
#     mock_entry = AsyncMock()
#     mock_entry.data = {"api_key": "test_api_key"}

#     # Initialize the coordinator
#     coordinator = OcadoUpdateCoordinator(hass, mock_entry)
#     coordinator.api_key = "test_api_key"  # Ensure the API key is set
#     coordinator.session = hass.helpers.aiohttp_client.async_get_clientsession(hass)

#     # Perform the update
#     await coordinator.async_refresh()

#     # Assert the data was fetched correctly
#     assert coordinator.last_update_success
#     assert coordinator.data[""] == data[""] #