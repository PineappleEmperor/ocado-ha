"""Sensor setup for Ocado UK Integration."""

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# from . import MyConfigEntry
from .const import (
    DOMAIN,
)
from .base import ExampleBaseEntity
from .coordinator import OcadoConfigEntry, OcadoUpdateCoordinator

PLATFORMS = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

# @dataclass
# class SensorTypeClass:
#     """Class for holding sensor type to sensor class."""

#     type: str
#     sensor_class: object


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OcadoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sensors."""
    # This gets the data update coordinator from the config entry runtime data as specified in your __init__.py
    coordinator: OcadoUpdateCoordinator = config_entry.runtime_data.coordinator
    sensors = [
        OcadoDelivery(coordinator),
        OcadoEdit(coordinator),
        OcadoBBDs(coordinator),
        OcadoOrderList(coordinator)
    ]
    async_add_entities(sensors)


class OcadoDelivery(ExampleBaseEntity, SensorEntity):
    """This sensor returns the next delivery information."""

    def __init__(self, coordinator: OcadoUpdateCoordinator) -> None:
        """Initialise the sensor."""
        # super().__init__(coordinator)
        self.coordinator = coordinator
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Next Delivery"
        self._attr_unique_id = "ocado_next_delivery"
        self._globalid = "ocado_next_delivery"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    # @callback
    # def _handle_coordinator_update(self) -> None:
    #     """Update sensor with latest data from coordinator."""
    #     # This method is called by your DataUpdateCoordinator when a successful update runs.
    #     # self.device = self.coordinator.get_device(self.device_id)
    #     _LOGGER.debug(
    #         "Updating device: %s, %s",
    #         self.device_id,
    #         self.coordinator.get_device_parameter(self.device_id, "device_name"),
    #     )
    #     self.async_write_ha_state()

    # @property
    # def native_value(self) -> int | float:
    #     """Return the state of the entity."""
    #     # Using native value and native unit of measurement, allows you to change units
    #     # in Lovelace and HA will automatically calculate the correct value.
    #     return self.coordinator.get_device_parameter(self.device_id, self.parameter)

    # @property
    # def name(self) -> str:
    #     """Return the name of the sensor."""
    #     return self.parameter.replace("_", " ").title()

    # @property
    # def unique_id(self) -> str:
    #     """Return unique id."""

    @property
    def state(self) -> Any:
        """Return the current state of the sensor."""
        return self._attr_state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._hass_custom_attributes

class ExampleCurrentSensor(ExampleBaseSensor):
    """Class to handle current sensors.

    This inherits the ExampleBaseSensor and so uses all the properties and methods
    from that class and then overrides specific attributes relevant to this sensor type.
    """

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_suggested_display_precision = 2


class ExampleEnergySensor(ExampleBaseSensor):
    """Class to handle energy sensors.

    This inherits the ExampleBaseSensor and so uses all the properties and methods
    from that class and then overrides specific attributes relevant to this sensor type.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR


class ExampleOffTimerSensor(ExampleBaseSensor):
    """Class to handle off timer sensors.

    This inherits the ExampleBaseSensor and so uses all the properties and methods
    from that class and then overrides specific attributes relevant to this sensor type.
    """


class ExampleTemperatureSensor(ExampleBaseSensor):
    """Class to handle temperature sensors.

    This inherits the ExampleBaseSensor and so uses all the properties and methods
    from that class and then overrides specific attributes relevant to this sensor type.
    """

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1


class ExampleVoltageSensor(ExampleBaseSensor):
    """Class to handle voltage sensors.

    This inherits the ExampleBaseSensor and so uses all the properties and methods
    from that class and then overrides specific attributes relevant to this sensor type.
    """

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 0