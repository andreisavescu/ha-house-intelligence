"""Diagnostic inventory and current-state sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HouseIntelligenceConfigEntry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HouseIntelligenceConfigEntry,
    async_add_entities,
) -> None:
    """Set up House Intelligence sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            HouseInventorySensor(coordinator, entry),
            HouseDataQualitySensor(coordinator, entry),
            HouseMeasurementFreshnessSensor(coordinator, entry),
        ]
    )


class HouseBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for House Intelligence sensors."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator, entry: ConfigEntry, key: str, name: str
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="House Intelligence",
            model="Home inventory and analysis",
        )


class HouseInventorySensor(HouseBaseSensor):
    """Total registered entities and inventory breakdowns."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "inventory", "Inventory")
        self._attr_icon = "mdi:home-analytics"

    @property
    def native_value(self):
        return self.coordinator.data["entities"]

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        keys = (
            "enabled_entities",
            "disabled_entities",
            "devices",
            "areas",
            "entities_without_device",
            "by_domain",
            "by_integration",
            "by_area",
            "by_device_class",
            "by_state_class",
            "by_unit",
            "by_manufacturer",
            "unavailable_by_integration",
            "without_area_by_integration",
        )
        return {key: data[key] for key in keys}


class HouseDataQualitySensor(HouseBaseSensor):
    """Counts inventory and measurement quality issues."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "data_quality", "Data quality")
        self._attr_icon = "mdi:clipboard-check-outline"

    @property
    def native_value(self):
        data = self.coordinator.data
        return (
            data["unavailable_entities"]
            + data["entities_without_area"]
            + data["measurement_stale"]
        )

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "unavailable_entities": data["unavailable_entities"],
            "entities_without_area": data["entities_without_area"],
            "entities_without_device": data["entities_without_device"],
            "disabled_entities": data["disabled_entities"],
            "measurement_stale": data["measurement_stale"],
            "measurement_unknown_age": data["measurement_unknown_age"],
            "unavailable_entity_sample": data["unavailable_sample"],
            "entities_without_area_sample": data["without_area_sample"],
            "stale_measurement_sample": data["measurement_stale_sample"],
            "sample_limit": data["diagnostic_sample_limit"],
        }


class HouseMeasurementFreshnessSensor(HouseBaseSensor):
    """Percentage of registered measurement sensors reporting recently."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-timeline-variant"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator, entry, "measurement_freshness", "Measurement freshness"
        )

    @property
    def native_value(self):
        return self.coordinator.data["measurement_fresh_percent"]

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "measurement_entities": data["measurement_entities"],
            "fresh": data["measurement_fresh"],
            "unavailable": data["measurement_unavailable"],
            "stale": data["measurement_stale"],
            "unknown_age": data["measurement_unknown_age"],
            "stale_after_hours": data["measurement_stale_after_hours"],
            "by_area": data["measurement_by_area"],
            "stale_entity_sample": data["measurement_stale_sample"],
            "unavailable_entity_sample": data["measurement_unavailable_sample"],
            "sample_limit": data["measurement_sample_limit"],
        }
