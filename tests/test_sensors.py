import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from pathlib import Path
# from custom_components.ocado.sensor import sensor
from custom_components.ocado.coordinator import OcadoUpdateCoordinator

# Load the fixture data
fixtures_path = Path(__file__).parent / "fixtures"

## No Data
with open(fixtures_path / "none.json") as file:
    no_data = json.load(file)

# @pytest.mark.asyncio
# async def test_x_sensor():
#     """Test the sensor with data from the x.json fixture."""
#     # Mock the coordinator
#     mock_coordinator = AsyncMock(spec=OcadoUpdateCoordinator)
#     mock_coordinator.data = recent_data

#     # Initialize the RecentShipment sensor
#     sensor = sensor(mock_coordinator)

#     # Call async_update to fetch data
#     await sensor.async_update()