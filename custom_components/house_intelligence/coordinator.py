"""Inventory coordinator."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, UPDATE_INTERVAL
from .inventory import build_inventory

_LOGGER = logging.getLogger(__name__)


class HouseInventoryCoordinator(DataUpdateCoordinator[dict]):
    """Collect the current Home Assistant inventory."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.hass = hass

    async def _async_update_data(self) -> dict:
        """Read registries and states without changing anything."""
        try:
            entity_registry = er.async_get(self.hass)
            device_registry = dr.async_get(self.hass)
            area_registry = ar.async_get(self.hass)
            return build_inventory(
                list(entity_registry.entities.values()),
                list(device_registry.devices.values()),
                list(area_registry.areas.values()),
                self.hass.states.async_all(),
            )
        except Exception as err:
            raise UpdateFailed(
                f"Unable to build Home Assistant inventory: {err}"
            ) from err
