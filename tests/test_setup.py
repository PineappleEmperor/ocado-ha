"""Tests for setting up and unloading the Ocado config entry."""

from unittest.mock import MagicMock

from custom_components.ocado import async_remove_config_entry_device
from custom_components.ocado.coordinator import OcadoUpdateCoordinator
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

EXPECTED_UNIQUE_IDS = {
    "ocado_latest_voucher",
    "ocado_next_delivery",
    "ocado_next_edit_deadline",
    "ocado_last_total",
    "ocado_upcoming_delivery",
    "ocado_orders",
    "ocado_missing_items",
    "ocado_substituted_items",
    "ocado_deliveries_calendar",
    "ocado_edit_deadlines_calendar",
}


async def test_setup_entry_loads_and_creates_entities(
    hass: HomeAssistant, init_integration
) -> None:
    """A config entry sets up to LOADED with its sensors and runtime coordinator."""
    assert init_integration.state is ConfigEntryState.LOADED
    assert isinstance(init_integration.runtime_data, OcadoUpdateCoordinator)

    entities = er.async_get(hass).entities.get_entries_for_config_entry_id(
        init_integration.entry_id
    )
    assert {entity.unique_id for entity in entities} == EXPECTED_UNIQUE_IDS

    by_unique_id = {entity.unique_id: entity for entity in entities}
    assert (
        by_unique_id["ocado_deliveries_calendar"].entity_id
        == "calendar.ocado_uk_deliveries"
    )


async def test_unload_entry(hass: HomeAssistant, init_integration) -> None:
    """Unloading a loaded config entry returns it to NOT_LOADED."""
    assert await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()
    assert init_integration.state is ConfigEntryState.NOT_LOADED


async def test_remove_config_entry_device_allowed(
    hass: HomeAssistant, init_integration
) -> None:
    """The device removal handler permits deletion so the UI shows a Delete button."""
    assert (
        await async_remove_config_entry_device(hass, init_integration, MagicMock())
        is True
    )
