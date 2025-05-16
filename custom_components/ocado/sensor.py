"""Sensor setup for Ocado UK Integration."""

# from dataclasses import dataclass
import logging
from typing import Any
from datetime import datetime
# import json

from homeassistant.components.sensor import (
    # SensorDeviceClass,
    SensorEntity,
    # SensorStateClass,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    # DataUpdateCoordinator,
    # UpdateFailed,
)

# from . import MyConfigEntry
from .const import (
    DAYS,
    DEVICE_CLASS,
    DOMAIN,
    # EMPTY_ATTRIBUTES,
)
from .coordinator import OcadoUpdateCoordinator
from .utils import (
    set_order,
    set_edit_order
)

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
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):# -> bool:
    """Set up the Sensors."""
    # This gets the data update coordinator from the config entry runtime data as specified in your __init__.py
    # coordinator: OcadoUpdateCoordinator = config_entry.runtime_data.coordinator
    coordinator: OcadoUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    _LOGGER.debug("Succesfully loaded coordinator.")


    sensors = [
        OcadoDelivery(coordinator),
        OcadoEdit(coordinator),
        OcadoUpcoming(coordinator),
        OcadoOrderList(coordinator)
    ]
    # TODO add a for loop to add bbd sensors, though will always be the weekdays + longer.
    # Create sensor entities
    
    # async_add_entities(
        
    # )
    # entities = create_sensor_entities(
    #     coordinator,
    # )
    # sensors.append(entities)
    _LOGGER.debug("Adding sensors.")
    async_add_entities(sensors, update_before_add=True)
    _LOGGER.debug("Sensors added.")
    # return True



def create_sensor_entities(coordinator, entry_id):
    """Create sensor entities based on coordinator data."""
    entities = []

    for day in DAYS:
        entities.append(
            OcadoBBDs(coordinator, day)
        )
    return entities


class OcadoDelivery(CoordinatorEntity, SensorEntity): # type: ignore
    """This sensor returns the next delivery information."""
    
    _attr_device_class = DEVICE_CLASS # type: ignore

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        # super().__init__(coordinator)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Next Delivery"
        self._attr_unique_id = "ocado_next_delivery"
        self._globalid = "ocado_next_delivery"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    @property
    def device_info(self) -> dict: # type: ignore
        """Return device information for device registry."""
        return {
            "identifiers": {(DOMAIN, "deliveries")},
            "name": "Ocado (UK) Deliveries",
            "manufacturer": "Ocado-ha",
            "model": "Delivery Sensor",
            "sw_version": "1.0",
        }

    @property
    def state(self) -> Any: # type: ignore
        """Return the current state of the sensor."""
        return self._attr_state

    @property
    def extra_state_attributes(self): # type: ignore
        """Return the state attributes of the sensor."""
        return self._hass_custom_attributes
    
    async def async_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        await self.coordinator.async_request_refresh()
        ocado_data = self.coordinator.data
        now = datetime.now()
        if ocado_data["next"]:
            order = ocado_data.get("next")
            result = set_order(self, order, now) # type: ignore
            if result is False:
                if ocado_data["upcoming"]:
                    order = ocado_data.get("upcoming")
                    result = set_order(self, order, now) # type: ignore
                    if not result:
                        self._attr_state = None
                        self._attr_icon = "mdi:help-circle"
                        attributes = {
                            "updated":      datetime.now(),
                            "order_number": None,
                            "delivery_datetime": None,
                            "delivery_window": None,
                            "edit_deadline": None,
                            "estimated_total": None,
                        }
                        self._hass_custom_attributes = attributes


class OcadoEdit(CoordinatorEntity, SensorEntity):
    """This sensor returns the next edit deadline information."""
    
    _attr_device_class = DEVICE_CLASS # type: ignore

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        # super().__init__(coordinator)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Next Edit Deadline"
        self._attr_unique_id = "ocado_next_edit_deadline"
        self._globalid = "ocado_next_edit_deadline"
        self._attr_icon = "mdi:text-box-edit"
        self._attr_state = None

    @property
    def device_info(self) -> dict: # type: ignore
        """Return device information for device registry."""
        return {
            "identifiers": {(DOMAIN, "deliveries")},
            "name": "Ocado (UK) Deliveries",
            "manufacturer": "Ocado-ha",
            "model": "Delivery Sensor",
            "sw_version": "1.0",
        }

    @property
    def state(self) -> Any: # type: ignore
        """Return the current state of the sensor."""
        return self._attr_state

    @property
    def extra_state_attributes(self): # type: ignore
        """Return the state attributes of the sensor."""
        return self._hass_custom_attributes
    
    async def async_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        await self.coordinator.async_request_refresh()
        ocado_data = self.coordinator.data
        now = datetime.now()
        if ocado_data["next"]:
            order = ocado_data.get("next")
            # If the latest order we have details about is before today, make it known.
            result = set_edit_order(self, order, now) # type: ignore
            if result is False:
                if ocado_data["upcoming"]:
                    order = ocado_data.get("upcoming")
                    result = set_edit_order(self, order, now) # type: ignore
                    if not result:
                        self._attr_state = None
                        self._attr_icon = "mdi:help-circle"
                        attributes = {
                            "updated":      datetime.now(),
                            "order_number": None,
                        }
                        self._hass_custom_attributes = attributes


class OcadoUpcoming(CoordinatorEntity, SensorEntity): # type: ignore
    """This sensor returns the next delivery information."""
    
    _attr_device_class = DEVICE_CLASS # type: ignore

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        # super().__init__(coordinator)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Upcoming Delivery"
        self._attr_unique_id = "ocado_upcoming_delivery"
        self._globalid = "ocado_upcoming_delivery"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    @property
    def device_info(self) -> dict: # type: ignore
        """Return device information for device registry."""
        return {
            "identifiers": {(DOMAIN, "deliveries")},
            "name": "Ocado (UK) Deliveries",
            "manufacturer": "Ocado-ha",
            "model": "Delivery Sensor",
            "sw_version": "1.0",
        }

    @property
    def state(self) -> Any:
        """Return the current state of the sensor."""
        return self._attr_state

    @property
    def extra_state_attributes(self): # type: ignore
        """Return the state attributes of the sensor."""
        return self._hass_custom_attributes
    
    async def async_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        await self.coordinator.async_request_refresh()
        ocado_data = self.coordinator.data
        now = datetime.now()
        _LOGGER.debug("Updating Upcoming sensor")
        if "upcoming" in ocado_data:
            order = ocado_data.get("upcoming")
            # If the latest order we have details about is before today, make it known.
            result = set_order(self, order, now) # type: ignore
            if not result:
                self._attr_state = None
                self._attr_icon = "mdi:help-circle"
                attributes = {
                    "updated":      datetime.now(),
                    "order_number": None,
                    "delivery_datetime": None,
                    "delivery_window": None,
                    "edit_deadline": None,
                    "estimated_total": None,
                }
                self._hass_custom_attributes = attributes


class OcadoOrderList(CoordinatorEntity, SensorEntity): # type: ignore
    """This sensor returns a list of all Ocado orders found."""

    _attr_device_class = DEVICE_CLASS # type: ignore

    # Disabled by default
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        # super().__init__(coordinator)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Orders"
        self._attr_unique_id = "ocado_orders"
        self._globalid = "ocado_orders"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    @property
    def device_info(self) -> dict: # type: ignore
        """Return device information for device registry."""
        return {
            "identifiers": {(DOMAIN, "deliveries")},
            "name": "Ocado (UK) Deliveries",
            "manufacturer": "Ocado-ha",
            "model": "Delivery Sensor",
            "sw_version": "1.0",
        }

    @property
    def state(self) -> Any: # type: ignore
        """Return the current state of the sensor."""
        return self._attr_state

    @property
    def extra_state_attributes(self): # type: ignore
        """Return the state attributes of the sensor."""
        return self._hass_custom_attributes
    
    async def async_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        await self.coordinator.async_request_refresh()
        ocado_data = self.coordinator.data
        if "orders" in ocado_data:
            orders = ocado_data.get("orders",[])

            self._attr_state = datetime.now() # type: ignore
            self._attr_icon = "mdi:clipboard-list"
            json_orders = []
            for order in orders:
                json_orders.append(order.toJSON())
            self._hass_custom_attributes = {
                "orders": json_orders
            }


class OcadoBBDs(SensorEntity):
    """This sensor returns the best before dates of the most recent delivery."""

    _attr_device_class = DEVICE_CLASS # type: ignore

    def __init__(self, coordinator: OcadoUpdateCoordinator, day: str) -> None:
        """Initialise the sensor."""
        # super().__init__(coordinator)
        self.coordinator = coordinator
        self.device_id = "Ocado BBDs"
        self._hass_custom_attributes = {}
        self._attr_name = f"Ocado BB {day.capitalize}"
        self._attr_unique_id = "ocado_bbd_{day}"
        # self._globalid = "ocado_bbds"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    @property
    def device_info(self) -> dict:
        """Return device information for device registry."""
        return {
            "identifiers": {(DOMAIN, "bbd")},
            "name": "Ocado (UK) Best Befores",
            "manufacturer": "Ocado-ha",
            "model": "Best Before Sensor",
            "sw_version": "1.0",
        }

    @property
    def state(self) -> Any: # type: ignore
        """Return the current state of the sensor."""
        return self._attr_state

    @property
    def extra_state_attributes(self): # type: ignore
        """Return the state attributes of the sensor."""
        return self._hass_custom_attributes
    
    async def async_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        await self.coordinator.async_request_refresh()
        ocado_data = self.coordinator.data
        if "orders" in ocado_data:
            orders = ocado_data.get("orders",[])

            self._attr_state = datetime.now() # type: ignore
            self._attr_icon = "mdi:clipboard-list"
            self._hass_custom_attributes = {
                "orders": orders
            }
