"""Pure inventory aggregation helpers.

This module deliberately has no Home Assistant imports so it can be tested
independently and reused by future analysis modules.
"""
from __future__ import annotations
from collections import Counter
from typing import Any

SAMPLE_LIMIT = 25

def _value(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a mapping or an object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _sorted_counts(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))

def build_inventory(entity_entries: list[Any], devices: list[Any], areas: list[Any], states: list[Any]) -> dict[str, Any]:
    """Build an inventory with bounded diagnostic samples and useful groupings."""
    state_by_id = {_value(state, "entity_id"): state for state in states}
    device_by_id = {_value(device, "id"): device for device in devices}
    area_by_id = {_value(area, "id"): area for area in areas}
    valid_entries = [entry for entry in entity_entries if _value(entry, "entity_id")]
    domain_counts: Counter[str] = Counter()
    integration_counts: Counter[str] = Counter()
    area_counts: Counter[str] = Counter()
    device_class_counts: Counter[str] = Counter()
    state_class_counts: Counter[str] = Counter()
    unit_counts: Counter[str] = Counter()
    manufacturer_counts: Counter[str] = Counter()
    unavailable_by_integration: Counter[str] = Counter()
    missing_area_by_integration: Counter[str] = Counter()
    unavailable: list[str] = []
    missing_area: list[str] = []
    enabled = disabled = entities_without_device = 0

    for entry in valid_entries:
        entity_id = _value(entry, "entity_id")
        integration = _value(entry, "platform") or "unknown"
        domain_counts[entity_id.split(".", 1)[0]] += 1
        integration_counts[integration] += 1
        if _value(entry, "disabled_by") is not None:
            disabled += 1
            continue
        enabled += 1
        state = state_by_id.get(entity_id)
        if state is None or _value(state, "state") in (None, "unavailable", "unknown"):
            unavailable.append(entity_id)
            unavailable_by_integration[integration] += 1
        attributes = _value(state, "attributes", {}) or {}
        for attribute, counter in (
            ("device_class", device_class_counts),
            ("state_class", state_class_counts),
            ("unit_of_measurement", unit_counts),
        ):
            value = attributes.get(attribute)
            if value not in (None, ""):
                counter[str(value)] += 1
        device_id = _value(entry, "device_id")
        device = device_by_id.get(device_id)
        if not device_id or device is None:
            entities_without_device += 1
        area_id = _value(entry, "area_id") or _value(device, "area_id")
        if area_id and area_id in area_by_id:
            area_counts[_value(area_by_id[area_id], "name", area_id)] += 1
        else:
            missing_area.append(entity_id)
            missing_area_by_integration[integration] += 1

    for device in devices:
        manufacturer = _value(device, "manufacturer")
        if manufacturer:
            manufacturer_counts[str(manufacturer)] += 1
    unavailable.sort()
    missing_area.sort()
    return {
        "entities": len(valid_entries), "enabled_entities": enabled, "disabled_entities": disabled,
        "devices": len(devices), "areas": len(areas),
        "unavailable_entities": len(unavailable), "entities_without_area": len(missing_area),
        "entities_without_device": entities_without_device,
        "by_domain": _sorted_counts(domain_counts), "by_integration": _sorted_counts(integration_counts),
        "by_area": _sorted_counts(area_counts), "by_device_class": _sorted_counts(device_class_counts),
        "by_state_class": _sorted_counts(state_class_counts), "by_unit": _sorted_counts(unit_counts),
        "by_manufacturer": _sorted_counts(manufacturer_counts),
        "unavailable_by_integration": _sorted_counts(unavailable_by_integration),
        "without_area_by_integration": _sorted_counts(missing_area_by_integration),
        "unavailable_sample": unavailable[:SAMPLE_LIMIT], "without_area_sample": missing_area[:SAMPLE_LIMIT],
        "diagnostic_sample_limit": SAMPLE_LIMIT,
    }
