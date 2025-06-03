# import pytest
# from homeassistant.core import HomeAssistant
# from homeassistant.helpers.entity_component import async_update_entity
# from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

# @pytest.mark.asyncio
# async def test_sensor_states(hass: HomeAssistant, init_integration):
#     """Test the states of the Ocado sensors."""
#     await async_update_entity(hass, "sensor.ocado_next_delivery")
#     state = hass.states.get("sensor.ocado_next_delivery")
#     assert state is not None
#     assert state.state != "unknown"
#     assert "delivery" in state.attributes.get("friendly_name", "").lower()
