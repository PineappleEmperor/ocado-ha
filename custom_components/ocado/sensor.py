"""Sensor setup for Ocado UK Integration."""

from dataclasses import dataclass
import logging
from typing import Any
from datetime import date, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

# from . import MyConfigEntry
from .const import (
    DEVICE_CLASS,
    DOMAIN,
    EMPTY_ATTRIBUTES,
)
from .coordinator import OcadoConfigEntry, OcadoUpdateCoordinator
from .utils import iconify, get_window

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
        OcadoBBDs(coordinator),
        OcadoDelivery(coordinator),
        OcadoOrderList(coordinator)
    ]
    async_add_entities(sensors)


class OcadoDelivery(CoordinatorEntity, SensorEntity):
    """This sensor returns the next delivery information."""
    
    _attr_device_class = DEVICE_CLASS

    def __init__(self, coordinator: OcadoUpdateCoordinator) -> None:
        """Initialise the sensor."""
        # super().__init__(coordinator)
        self.coordinator = coordinator
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Next"
        self._attr_unique_id = "ocado_next_delivery"
        self._globalid = "ocado_next_delivery"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    @property
    def device_info(self) -> dict:
        """Return device information for device registry."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": f"{self.coordinator.name} {self.}",
            "manufacturer": "Ocado-ha",
            "model": "Delivery Sensor",
            "sw_version": "1.0",
        }

    @property
    def state(self) -> Any:
        """Return the current state of the sensor."""
        return self._attr_state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._hass_custom_attributes
    
    async def async_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        await self.coordinator.async_request_refresh()
        ocado_data = self.coordinator.data
        today = date.today()
        if ocado_data["next"]:
            order = ocado_data.get("next")
            # If the latest order we have details about is before today, make it known.
            if order.delivery_datetime.date() < today:
                if ocado_data["upcoming"]:
                    order = ocado_data.get("upcoming")
                    if order.delivery_datetime.date() >= today:
                        days_until_next_delivery = (order.delivery_date - today).days
                        self._attr_state = order.updated
                        self._attr_icon = iconify(days_until_next_delivery)
                        attributes = {
                            "order_number": order.order_number,
                            "delivery_date": order.delivery_datetime.date(),
                            "delivery_window": get_window(order.delivery_datetime, order.delivery_window_end),
                            "edit_date": order.edit_datetime.date(),
                            "edit_time": order.edit_datetime.strftime("%H:%M"),
                            "estimated_total": order.estimated_total,
                        }
                        self._hass_custom_attributes = attributes                        
                    else:
                        self._attr_state = datetime.now()
                        self._attr_icon = "mdi:help-circle"
                        self._hass_custom_attributes = EMPTY_ATTRIBUTES
                else:
                    self._attr_state = datetime.now()
                    self._attr_icon = "mdi:help-circle"
                    attributes = {
                        "delivery_date": None,
                        "delivery_window": None,
                        "edit_date": None,
                        "edit_time": None,
                        "estimated_total": None,
                    }
                    self._hass_custom_attributes = attributes
            else:
                days_until_next_delivery = (order.delivery_date - today).days
                self._attr_state = order.updated
                self._attr_icon = iconify(days_until_next_delivery)
                attributes = {
                    "order_number": order.order_number,
                    "delivery_date": order.delivery_datetime.date(),
                    "delivery_window": get_window(order.delivery_datetime, order.delivery_window_end),
                    "edit_date": order.edit_datetime.date(),
                    "edit_time": order.edit_datetime.strftime("%H:%M"),
                    "estimated_total": order.estimated_total,
                }
                self._hass_custom_attributes = attributes


class OcadoOrderList(SensorEntity):
    """This sensor returns the next delivery information."""

    def __init__(self, coordinator: OcadoUpdateCoordinator) -> None:
        """Initialise the sensor."""
        # super().__init__(coordinator)
        self.coordinator = coordinator
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Orders"
        self._attr_unique_id = "ocado_orders"
        self._globalid = "ocado_orders"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    @property
    def state(self) -> Any:
        """Return the current state of the sensor."""
        return self._attr_state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._hass_custom_attributes
    
    async def async_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        await self.coordinator.async_request_refresh()
        ocado_data = self.coordinator.data
        orders = ocado_data.get("list",[])

        self._attr_state = datetime.now()
        self._attr_icon = "mdi:clipboard-list"
        self._hass_custom_attributes = {
            "orders": orders
        }

# This should be a device with an entity for each day
class OcadoBBDs(SensorEntity):
    """This sensor returns the next delivery information."""

    def __init__(self, coordinator: OcadoUpdateCoordinator) -> None:
        """Initialise the sensor."""
        # super().__init__(coordinator)
        self.coordinator = coordinator
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado BBDs"
        self._attr_unique_id = "ocado_bbds"
        self._globalid = "ocado_bbds"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    @property
    def state(self) -> Any:
        """Return the current state of the sensor."""
        return self._attr_state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._hass_custom_attributes
    
    async def async_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        await self.coordinator.async_request_refresh()
        ocado_data = self.coordinator.data
        orders = ocado_data.get("list",[])

        self._attr_state = datetime.now()
        self._attr_icon = "mdi:clipboard-list"
        self._hass_custom_attributes = {
            "orders": orders
        }
