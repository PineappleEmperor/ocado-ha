"""Base entity and device info for the Ocado integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OcadoUpdateCoordinator


def ocado_device_info(version: str) -> DeviceInfo:
    """Build the shared Ocado delivery device, stamping the integration version."""
    return DeviceInfo(
        identifiers={(DOMAIN, "deliveries")},
        name="Ocado (UK) Deliveries",
        manufacturer="Ocado-ha",
        model="Delivery Sensor",
        sw_version=version,
    )


class OcadoEntity(CoordinatorEntity[OcadoUpdateCoordinator]):
    """Base entity attaching every Ocado sensor to the one delivery device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OcadoUpdateCoordinator) -> None:
        """Initialise the entity with the shared device info."""
        super().__init__(coordinator)
        self._attr_device_info = ocado_device_info(coordinator.version)
