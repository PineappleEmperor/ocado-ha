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
    SensorDeviceClass,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
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
    WEEKDAY_MAP,
    # EMPTY_ATTRIBUTES,
)
from .coordinator import OcadoUpdateCoordinator
from .utils import (
    set_order,
    set_edit_order,
    set_bbds,
    set_total,
    detect_attr_changes,
    has_delivery_window_end,
    has_edit_datetime,
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
        OcadoTotal(coordinator),
        OcadoUpcoming(coordinator),
        OcadoOrderList(coordinator)
    ]
    sensors = sensors + create_bbd_sensor_entities(coordinator)
    
    _LOGGER.debug("Adding sensors.")
    async_add_entities(sensors, update_before_add=True)
    _LOGGER.debug("Sensors added.")
    # return True



def create_bbd_sensor_entities(coordinator):#, entry_id):
    """Create bbd sensor entities based on coordinator data."""
    entities = []
    for day in DAYS[:-1]:
        entities.append(
            OcadoBBDs(coordinator, day)
        )
    return entities


class OcadoDelivery(CoordinatorEntity, SensorEntity): # type: ignore
    """This sensor returns the next delivery information."""
    
    _attr_device_class = DEVICE_CLASS # type: ignore

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Next Delivery"
        self._attr_unique_id = "ocado_next_delivery"
        self._globalid = "ocado_next_delivery"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    async def async_added_to_hass(self):
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates from the coordinator and refresh sensor state."""
        _LOGGER.debug("Handling coordinator update for %s", self.entity_id)
        
        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_state = None
                self._attr_icon = "mdi:help-circle"
                self._hass_custom_attributes = {
                    "updated":      datetime.now(),
                    "order_number": None,
                }
                return
            else:
                return
        
        now = datetime.now()
        # order = ocado_data.get("next") or ocado_data.get("upcoming")
        # Switch between orders depending on delivery datetime or output None
        order = ocado_data.get("next")
        if (order is None):
            # I don't think this will ever fire
            order = ocado_data.get("upcoming")
            if has_delivery_window_end(order):
                if order.delivery_window_end < now: # type: ignore
                    order = None
            else:
                order = None
        if has_delivery_window_end(order):
            # If the delivery datetime is in the past check upcoming
            if (order.delivery_window_end < now): # type: ignore
                order = ocado_data.get("upcoming")
                if has_delivery_window_end(order):
                    if (order.delivery_window_end < now): # type: ignore
                        order = None
                else:
                    order = None
        if order is not None:
            result = set_order(self, order, now) # type: ignore
            _LOGGER.debug("Set_order returned %s", result)
        else:
            self._attr_state = None
            self._attr_icon = "mdi:help-circle"
            self._hass_custom_attributes = {
                "updated":      datetime.now(),
                "order_number": None,
                "delivery_datetime": None,
                "delivery_window": None,
                "edit_deadline": None,
                "estimated_total": None,
            }
        # Check if the attributes need updating
        if self.entity_id is not None:
            current = self.hass.states.get(self.entity_id)
            new = self._hass_custom_attributes
            
            if current is None:
                self.async_write_ha_state()
                return
            
            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
            # Now check if the edit deadline has passed
            elif "next" in current.attributes:
                if hasattr(current.attributes.get("next"),"edit_deadline"):
                    if current.attributes.get("next").edit_deadline < now: # type: ignore
                        _LOGGER.debug("Updating due to edit deadline passed")
                        self.async_write_ha_state()


class OcadoEdit(CoordinatorEntity, SensorEntity): # type: ignore
    """This sensor returns the next edit deadline information."""
    
    _attr_device_class = DEVICE_CLASS # type: ignore

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Next Edit Deadline"
        self._attr_unique_id = "ocado_next_edit_deadline"
        self._globalid = "ocado_next_edit_deadline"
        self._attr_icon = "mdi:text-box-edit"
        self._attr_state = None

    async def async_added_to_hass(self):
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

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
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        _LOGGER.debug("Updating the edit sensor")
        
        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_state = None
                self._attr_icon = "mdi:help-circle"
                self._hass_custom_attributes = {
                    "updated":      datetime.now(),
                    "order_number": None,
                }
                return
            else:
                return
        
        now = datetime.now()        
        # Switch between orders depending on edit deadlines or output None
        order = ocado_data.get("next")
        if (order is None):
            order = ocado_data.get("upcoming")
            if has_edit_datetime(order):
                if order.edit_datetime < now: # type: ignore
                    order = None
            else:
                order = None
        if has_edit_datetime(order):
            # If the edit datetime is in the past check upcoming
            if (order.edit_datetime < now): # type: ignore
                order = ocado_data.get("upcoming")
                if has_edit_datetime(order):
                    # If the edit datetime is in the past return empty
                    if order.edit_datetime < now: # type: ignore
                        self._attr_state = None
                        self._attr_icon = "mdi:help-circle"
                        self._hass_custom_attributes = {
                            "updated":      datetime.now(),
                            "order_number": None,
                        }
                    else:
                        result = set_edit_order(self, order, now) # type: ignore
                        _LOGGER.debug("Set_order returned %s", result)                        
                else:
                    self._attr_state = None
                    self._attr_icon = "mdi:help-circle"
                    self._hass_custom_attributes = {
                        "updated":      datetime.now(),
                        "order_number": None,
                    }
            else:
                # Set the edit order with the selected order
                result = set_edit_order(self, order, now) # type: ignore
                _LOGGER.debug("Set_order returned %s", result)
        else:
            # If no orders are returned, return an empty order
            self._attr_state = None
            self._attr_icon = "mdi:help-circle"
            self._hass_custom_attributes = {
                "updated":      datetime.now(),
                "order_number": None,
            }
        # Check if the attributes need updating
        if self.entity_id is not None:
            current = self.hass.states.get(self.entity_id)
            new = self._hass_custom_attributes
            
            if current is None:
                self.async_write_ha_state()
                return
            
            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
            # Now check if the edit deadline has passed -> what if there is no next? Display 
            elif "next" in current.attributes:
                if hasattr(current.attributes.get("next"),"edit_deadline"):
                    if current.attributes.get("next").edit_deadline < now: # type: ignore
                        _LOGGER.debug("Updating due to edit deadline passed")
                        self.async_write_ha_state()


class OcadoTotal(CoordinatorEntity, SensorEntity): # type: ignore
    """This sensor returns the next edit deadline information."""
    
    _attr_device_class = DEVICE_CLASS # type: ignore

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Last Total"
        self._attr_unique_id = "ocado_last_total"
        self._globalid = "ocado_last_total"
        self._attr_icon = "mdi:receipt-text"
        self._attr_state = None

    async def async_added_to_hass(self):
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

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
    
    @property
    def device_class(self): # type: ignore
        """The type of sensor"""
        return SensorDeviceClass.MONETARY
    
    @property
    def native_unit_of_measurement(self): # type: ignore
        """The unit of measurement of sensor"""
        return "GBP"
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        _LOGGER.debug("Updating the last total sensor")
        
        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_state = None
                self._attr_icon = "mdi:help-circle"
                self._hass_custom_attributes = {
                    "updated":      datetime.now(),
                    "order_number": None,
                }
                return
            else:
                return
        
        now = datetime.now()
        order = ocado_data.get("total")
        if order is not None:
            result = set_total(self, order, now) # noqa: F841
            _LOGGER.debug("Set_total returned %s", result)
        else:
            self._attr_state = None
            self._attr_icon = "mdi:help-circle"
            self._hass_custom_attributes = {
                "updated":      datetime.now(),
                "order_number": None,
            }
        if self.entity_id is not None:
            current = self.hass.states.get(self.entity_id)
            new = self._hass_custom_attributes
            
            if current is None:
                self.async_write_ha_state()
                return
            
            old = current.attributes
            if detect_attr_changes(new, old): # type: ignore
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()


class OcadoUpcoming(CoordinatorEntity, SensorEntity): # type: ignore
    """This sensor returns the next delivery information."""
    
    _attr_device_class = DEVICE_CLASS # type: ignore

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Upcoming Delivery"
        self._attr_unique_id = "ocado_upcoming_delivery"
        self._globalid = "ocado_upcoming_delivery"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    async def async_added_to_hass(self):
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

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
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        _LOGGER.debug("Handling coordinator update for %s", self.entity_id)
        
        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_state = None
                self._attr_icon = "mdi:help-circle"
                self._hass_custom_attributes = {
                    "updated":      datetime.now(),
                    "order_number": None,
                }
                return
            else:
                return
        
        now = datetime.now()
        order = ocado_data.get("upcoming")
        
        if order is not None:
            result = set_order(self, order, now) # type: ignore
            _LOGGER.debug("Set_order returned %s", result)
        else:            
            self._attr_state = None
            self._attr_icon = "mdi:help-circle"
            self._hass_custom_attributes = {
                "updated":      datetime.now(),
                "order_number": None,
                "delivery_datetime": None,
                "delivery_window": None,
                "edit_deadline": None,
                "estimated_total": None,
            }
        # Check if the attributes need updating
        if self.entity_id is not None:
            current = self.hass.states.get(self.entity_id)
            new = self._hass_custom_attributes
            
            if current is None:
                self.async_write_ha_state()
                return
            
            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
            # Now check if the edit deadline has passed
            elif "next" in current.attributes:
                if hasattr(current.attributes.get("next"),"edit_deadline"):
                    if current.attributes.get("next").edit_deadline < now: # type: ignore
                        _LOGGER.debug("Updating due to edit deadline passed")
                        self.async_write_ha_state()
            



class OcadoOrderList(CoordinatorEntity, SensorEntity): # type: ignore
    """This sensor returns a list of all Ocado orders found."""

    _attr_device_class = DEVICE_CLASS # type: ignore

    # Disabled by default
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._hass_custom_attributes = {}
        self._attr_name = "Ocado Orders"
        self._attr_unique_id = "ocado_orders"
        self._globalid = "ocado_orders"
        self._attr_icon = "mdi:cart-outline"
        self._attr_state = None

    async def async_added_to_hass(self):
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

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
    
    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        
        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_state = None
                self._attr_icon = "mdi:help-circle"
                self._hass_custom_attributes = {
                    "orders":      [],
                }
                return
            else:
                return
        
        orders = ocado_data.get("orders")
        if orders is not None:
            self._attr_state = datetime.now() # type: ignore
            self._attr_icon = "mdi:clipboard-list"
            json_orders = []
            for order in orders:
                json_orders.append(order.toJSON())
            self._hass_custom_attributes = {
                "orders": json_orders
            }
        else:
            self._attr_state = None
            self._attr_icon = "mdi:help-circle"
            self._hass_custom_attributes = {
                "orders": []
            }
        # Check if the attributes need updating
        if self.entity_id is not None:
            now = datetime.now()
            current = self.hass.states.get(self.entity_id)
            new = self._hass_custom_attributes
            
            if current is None:
                self.async_write_ha_state()
                return
            
            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
            # Now check if the edit deadline has passed
            elif "next" in current.attributes:
                if hasattr(current.attributes.get("next"),"edit_deadline"):
                    if current.attributes.get("next").edit_deadline < now: # type: ignore
                        _LOGGER.debug("Updating due to edit deadline passed")
                        self.async_write_ha_state()


class OcadoBBDs(CoordinatorEntity, SensorEntity): # type: ignore
    """This sensor returns the best before dates of the most recent delivery."""

    _attr_device_class = DEVICE_CLASS # type: ignore

    # Disabled by default
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: OcadoUpdateCoordinator, day: str, context: Any = None,) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context) # type: ignore
        self.coordinator                = coordinator
        self.device_id                  = "Ocado BBDs"
        self._hass_custom_attributes    = {}
        self._attr_name                 = f"Ocado Best Before {WEEKDAY_MAP[day].capitalize()}"
        self._attr_unique_id            = f"ocado_bbd_{day}"
        self._globalid                  = f"ocado_bbds_{day}"
        self._attr_icon                 = "mdi:cart-outline"
        self._attr_state                = None
        self._day                       = day

    async def async_added_to_hass(self):
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

    @property
    def device_info(self) -> dict: # type: ignore
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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        _LOGGER.debug("Handling coordinator update for %s", self.entity_id)
        
        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_state = None
                self._attr_icon = "mdi:help-circle"
                self._hass_custom_attributes = {
                    "updated"        : datetime.now(),
                    "order_number"   : None,
                    "date"           : None,
                    "bbds"           : [],
                }
                return
            else:
                return
        
        now = datetime.now()
        day_list = ocado_data.get("receipt")
        
        if day_list is not None:
            result = set_bbds(self, day_list, self._day, now) # type: ignore
            _LOGGER.debug("Set_bbds returned %s", result)
        else:            
            self._attr_state = None
            self._attr_icon = "mdi:help-circle"
            self._hass_custom_attributes = {
                "updated"       : datetime.now(),
                "order_number"  : None,
                "date"          : None,
                "bbds"          : None,
            }
        # Check if the attributes need updating
        if self.entity_id is not None:
            current = self.hass.states.get(self.entity_id)
            new = self._hass_custom_attributes
            
            if current is None:
                self.async_write_ha_state()
                return
            
            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
