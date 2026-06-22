"""Sensor setup for Ocado UK Integration."""

# from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DAYS,
    DOMAIN,
    OCADO_BBD_DEVICE_DESCRIPTION,
    OCADO_DELIVERY_DEVICE_DESCRIPTION,
    WEEKDAY_MAP,
    OcadoOrder,
)
from .coordinator import OcadoUpdateCoordinator
from .utils import detect_attr_changes, set_bbds, set_edit_order, set_order, set_voucher

PLATFORMS = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


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
        OcadoOrderList(coordinator),
        OcadoVoucher(coordinator)
    ]
    sensors = sensors + create_bbd_sensor_entities(coordinator)

    _LOGGER.debug("Adding sensors.")
    async_add_entities(sensors, update_before_add=True)
    _LOGGER.debug("Sensors added.")
    # return True



def create_bbd_sensor_entities(coordinator):#, entry_id):
    """Create bbd sensor entities based on coordinator data."""
    return [OcadoBBDs(coordinator, day) for day in DAYS[:-1]]


class OcadoVoucher(CoordinatorEntity, SensorEntity):
    """This sensor returns the latest voucher information if it's available."""


    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._attr_device_info = OCADO_DELIVERY_DEVICE_DESCRIPTION
        self._attr_extra_state_attributes = {}
        self._attr_name = "Ocado Latest Voucher"
        self._attr_unique_id = "ocado_latest_voucher"
        self._globalid = "ocado_latest_voucher"
        self._attr_icon = "mdi:receipt"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "GBP"
        self._attr_native_value = None

    async def async_added_to_hass(self):
        """Add to HA."""
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates from the coordinator and refresh sensor state."""
        _LOGGER.debug("Handling coordinator update for %s", self.entity_id)

        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_native_value = None
                self._attr_icon = "mdi:help-circle"
                self._attr_extra_state_attributes = {
                    "updated":      datetime.now(),
                    "voucher": None,
                    "amount": None,
                    "valid_until": None,
                }
                return
            return

        now = datetime.now()
        # order = ocado_data.get("next") or ocado_data.get("upcoming")
        # Switch between orders depending on delivery datetime or output None
        voucher = ocado_data.get("voucher")
        if voucher is not None:
            result = set_voucher(self, voucher, now)
            _LOGGER.debug("Set_voucher returned %s", result)
        else:
            self._attr_native_value = None
            self._attr_icon = "mdi:help-circle"
            self._attr_extra_state_attributes = {
                "updated":      datetime.now(),
                "voucher": None,
                "amount": None,
                "valid_until": None,
            }
        # Check if the attributes need updating
        if self.entity_id is not None:
            current = self.hass.states.get(self.entity_id)
            new = self._attr_extra_state_attributes

            if current is None:
                self.async_write_ha_state()
                return

            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()


class OcadoDelivery(CoordinatorEntity, SensorEntity):
    """This sensor returns the next delivery information."""


    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._attr_device_info = OCADO_DELIVERY_DEVICE_DESCRIPTION
        self._attr_extra_state_attributes = {}
        self._attr_name = "Ocado Next Delivery"
        self._attr_unique_id = "ocado_next_delivery"
        self._globalid = "ocado_next_delivery"
        self._attr_icon = "mdi:cart-outline"
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to Home Assistant."""
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updates from the coordinator and refresh sensor state."""
        _LOGGER.debug("Handling coordinator update for %s", self.entity_id)

        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_native_value = None
                self._attr_icon = "mdi:help-circle"
                self._attr_extra_state_attributes = {
                    "updated":      datetime.now(),
                    "order_number": None,
                }
                return
            return

        now = datetime.now()
        # order = ocado_data.get("next") or ocado_data.get("upcoming")
        # Switch between orders depending on delivery datetime or output None
        order = ocado_data.get("next")
        if order is None:
            # I don't think this will ever fire
            order = ocado_data.get("upcoming")
            if order is not None and order.delivery_window_end is not None:
                if order.delivery_window_end < now:
                    order = None
            else:
                order = None
        if order is not None and order.delivery_window_end is not None:
            # If the delivery datetime is in the past check upcoming
            if order.delivery_window_end < now:
                order = ocado_data.get("upcoming")
                if order is not None and order.delivery_window_end is not None:
                    if order.delivery_window_end < now:
                        order = None
                else:
                    order = None
        if order is not None:
            result = set_order(self, order, now)
            _LOGGER.debug("Set_order returned %s", result)
        else:
            self._attr_native_value = None
            self._attr_icon = "mdi:help-circle"
            self._attr_extra_state_attributes = {
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
            new = self._attr_extra_state_attributes

            if current is None:
                self.async_write_ha_state()
                return

            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
            # Now check if the edit deadline has passed
            elif "next" in current.attributes:
                next_attr = current.attributes.get("next")
                if next_attr is not None and hasattr(next_attr, "edit_deadline") and next_attr.edit_deadline < now:
                    _LOGGER.debug("Updating due to edit deadline passed")
                    self.async_write_ha_state()


class OcadoEdit(CoordinatorEntity, SensorEntity):
    """This sensor returns the next edit deadline information."""


    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._attr_device_info = OCADO_DELIVERY_DEVICE_DESCRIPTION
        self._attr_extra_state_attributes = {}
        self._attr_name = "Ocado Next Edit Deadline"
        self._attr_unique_id = "ocado_next_edit_deadline"
        self._globalid = "ocado_next_edit_deadline"
        self._attr_icon = "mdi:text-box-edit"
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to Home Assistant."""
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        _LOGGER.debug("Updating the edit sensor")

        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_native_value = None
                self._attr_icon = "mdi:help-circle"
                self._attr_extra_state_attributes = {
                    "updated":      datetime.now(),
                    "order_number": None,
                }
                return
            return

        now = datetime.now()
        # Switch between orders depending on edit deadlines or output None
        order = ocado_data.get("next")
        if order is None:
            order = ocado_data.get("upcoming")
            if order is not None and order.edit_datetime is not None:
                if order.edit_datetime < now:
                    order = None
            else:
                order = None
        if order is not None and order.edit_datetime is not None:
            # If the edit datetime is in the past check upcoming
            if order.edit_datetime < now:
                order = ocado_data.get("upcoming")
                if order is not None and order.edit_datetime is not None:
                    # If the edit datetime is in the past return empty
                    if order.edit_datetime < now:
                        self._attr_native_value = None
                        self._attr_icon = "mdi:help-circle"
                        self._attr_extra_state_attributes = {
                            "updated":      datetime.now(),
                            "order_number": None,
                        }
                    else:
                        result = set_edit_order(self, order, now)
                        _LOGGER.debug("Set_order returned %s", result)
                else:
                    self._attr_native_value = None
                    self._attr_icon = "mdi:help-circle"
                    self._attr_extra_state_attributes = {
                        "updated":      datetime.now(),
                        "order_number": None,
                    }
            else:
                # Set the edit order with the selected order
                result = set_edit_order(self, order, now)
                _LOGGER.debug("Set_order returned %s", result)
        else:
            # If no orders are returned, return an empty order
            self._attr_native_value = None
            self._attr_icon = "mdi:help-circle"
            self._attr_extra_state_attributes = {
                "updated":      datetime.now(),
                "order_number": None,
            }
        # Check if the attributes need updating
        if self.entity_id is not None:
            current = self.hass.states.get(self.entity_id)
            new = self._attr_extra_state_attributes

            if current is None:
                self.async_write_ha_state()
                return

            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
            # Now check if the edit deadline has passed -> what if there is no next? Display
            elif "next" in current.attributes:
                next_attr = current.attributes.get("next")
                if next_attr is not None and hasattr(next_attr, "edit_deadline") and next_attr.edit_deadline < now:
                    _LOGGER.debug("Updating due to edit deadline passed")
                    self.async_write_ha_state()


class OcadoTotal(CoordinatorEntity[OcadoUpdateCoordinator], SensorEntity):
    """This sensor returns the next edit deadline information."""

    entity_description = SensorEntityDescription(
        key                         = "ocado_last_total",
        name                        = "Ocado Last Total",
        device_class                = SensorDeviceClass.MONETARY,
        native_unit_of_measurement  = "GBP",
        icon                        = "mdi:receipt-text",
    )
    _attr_has_entity_name = True

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self._attr_unique_id        = f"ocado_last_total_{context}" if context else "ocado_last_total"
        self._attr_device_info      = OCADO_DELIVERY_DEVICE_DESCRIPTION
        self._attr_extra_state_attributes: dict[str, Any] = {}

    def _set_total(self, order: OcadoOrder) -> None:
        """This function validates an order is in the future and sets the state and attributes if it is."""
        _LOGGER.debug("Setting total order")
        if order.estimated_total is not None:
                self._attr_native_value = order.estimated_total
                self._attr_icon = "mdi:receipt-text"
                self._attr_extra_state_attributes = {
                    "updated"               : order.updated,
                    "order_number"          : order.order_number,
                }

    def _null_state(self) -> None:
        """Set the sensor to a null state."""
        self._attr_native_value = None
        self._attr_icon = "mdi:help-circle"
        self._attr_extra_state_attributes = {
            "updated":      dt_util.now(),
            "order_number": None,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        _LOGGER.debug("Updating the last total sensor")

        ocado_data = self.coordinator.data
        total = ocado_data.get("total") if ocado_data else None
        if total:
            self._set_total(total)
        else:
            self._null_state()
        super()._handle_coordinator_update()


class OcadoUpcoming(CoordinatorEntity, SensorEntity):
    """This sensor returns the next delivery information."""


    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._attr_device_info = OCADO_DELIVERY_DEVICE_DESCRIPTION
        self._attr_extra_state_attributes = {}
        self._attr_name = "Ocado Upcoming Delivery"
        self._attr_unique_id = "ocado_upcoming_delivery"
        self._globalid = "ocado_upcoming_delivery"
        self._attr_icon = "mdi:cart-outline"
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to Home Assistant."""
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        _LOGGER.debug("Handling coordinator update for %s", self.entity_id)

        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_native_value = None
                self._attr_icon = "mdi:help-circle"
                self._attr_extra_state_attributes = {
                    "updated":      datetime.now(),
                    "order_number": None,
                }
                return
            return

        now = datetime.now()
        order = ocado_data.get("upcoming")

        if order is not None:
            result = set_order(self, order, now)
            _LOGGER.debug("Set_order returned %s", result)
        else:
            self._attr_native_value = None
            self._attr_icon = "mdi:help-circle"
            self._attr_extra_state_attributes = {
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
            new = self._attr_extra_state_attributes

            if current is None:
                self.async_write_ha_state()
                return

            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
            # Now check if the edit deadline has passed
            elif "next" in current.attributes:
                next_attr = current.attributes.get("next")
                if next_attr is not None and hasattr(next_attr, "edit_deadline") and next_attr.edit_deadline < now:
                    _LOGGER.debug("Updating due to edit deadline passed")
                    self.async_write_ha_state()


class OcadoOrderList(CoordinatorEntity, SensorEntity):
    """This sensor returns a list of all Ocado orders found."""


    # Disabled by default
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: OcadoUpdateCoordinator, context: Any = None) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator = coordinator
        self.coordinator_context = context
        self.device_id = "Ocado Deliveries"
        self._attr_device_info = OCADO_DELIVERY_DEVICE_DESCRIPTION
        self._attr_extra_state_attributes = {}
        self._attr_name = "Ocado Orders"
        self._attr_unique_id = "ocado_orders"
        self._globalid = "ocado_orders"
        self._attr_icon = "mdi:cart-outline"
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to Home Assistant."""
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""

        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_native_value = None
                self._attr_icon = "mdi:help-circle"
                self._attr_extra_state_attributes = {
                    "orders":      [],
                }
                return
            return

        orders = ocado_data.get("orders")
        if orders is not None:
            self._attr_native_value = datetime.now()
            self._attr_icon = "mdi:clipboard-list"
            json_orders = [order.toJSON() for order in orders]
            self._attr_extra_state_attributes = {
                "orders": json_orders
            }
        else:
            self._attr_native_value = None
            self._attr_icon = "mdi:help-circle"
            self._attr_extra_state_attributes = {
                "orders": []
            }
        # Check if the attributes need updating
        if self.entity_id is not None:
            now = datetime.now()
            current = self.hass.states.get(self.entity_id)
            new = self._attr_extra_state_attributes

            if current is None:
                self.async_write_ha_state()
                return

            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
            # Now check if the edit deadline has passed
            elif "next" in current.attributes:
                next_attr = current.attributes.get("next")
                if next_attr is not None and hasattr(next_attr, "edit_deadline") and next_attr.edit_deadline < now:
                    _LOGGER.debug("Updating due to edit deadline passed")
                    self.async_write_ha_state()


class OcadoBBDs(RestoreEntity, CoordinatorEntity, SensorEntity):
    """This sensor returns the best before dates of the most recent delivery."""

    # Disabled by default
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: OcadoUpdateCoordinator, day: str, context: Any = None,) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, context=context)
        self.coordinator                = coordinator
        self.device_id                  = "Ocado BBDs"
        self._attr_device_info          = OCADO_BBD_DEVICE_DESCRIPTION
        self._attr_extra_state_attributes    = {}
        self._attr_name                 = f"Ocado Best Before {WEEKDAY_MAP[day].capitalize()}"
        self._attr_unique_id            = f"ocado_bbd_{day}"
        self._globalid                  = f"ocado_bbds_{day}"
        self._attr_icon                 = "mdi:cart-outline"
        self._attr_native_value                = None
        self._day                       = day

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        _LOGGER.debug("Running async_added_to_hass")
        await super().async_added_to_hass()

        if (old_state := await self.async_get_last_state()) is not None:
            self._attr_native_value = old_state.state
            self._attr_extra_state_attributes = dict(old_state.attributes)


    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch the latest data from the coordinator."""
        _LOGGER.debug("Handling coordinator update for %s", self.entity_id)

        ocado_data = self.coordinator.data
        if not ocado_data:
            if self.entity_id is None:
                _LOGGER.warning("Coordinator data is None for %s", self.entity_id)
                self._attr_native_value = None
                self._attr_icon = "mdi:help-circle"
                self._attr_extra_state_attributes = {
                    "updated"        : datetime.now(),
                    "order_number"   : None,
                    "date"           : None,
                    "bbds"           : [],
                }
                return
            return

        now = datetime.now()
        day_list = ocado_data.get("receipt")

        if day_list is not None:
            result = set_bbds(self, day_list, self._day, now)
            _LOGGER.debug("Set_bbds returned %s", result)
        else:
            self._attr_native_value = None
            self._attr_icon = "mdi:help-circle"
            self._attr_extra_state_attributes = {
                "updated"       : datetime.now(),
                "order_number"  : None,
                "date"          : None,
                "bbds"          : None,
            }
        # Check if the attributes need updating
        if self.entity_id is not None:
            current = self.hass.states.get(self.entity_id)
            new = self._attr_extra_state_attributes

            if current is None:
                self.async_write_ha_state()
                return

            old = current.attributes
            if detect_attr_changes(new, old):
                _LOGGER.debug("Updating due to new attributes")
                self.async_write_ha_state()
