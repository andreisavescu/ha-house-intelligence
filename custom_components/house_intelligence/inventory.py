"""Pure inventory aggregation helpers.

Kept independent of Home Assistant imports so the aggregation can be tested
without starting a Home Assistant instance.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def _value(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a mapping or an object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def build_inventory(
    entity_entries: list[Any],
    devices: list[Any],
    areas: list[Any],
    states: list[Any],
) -> dict[str, Any]:
    """Build a compact inventory from registry entries and current states."""
    state_by_id = {_value(state, "entity_id"): state for state in states}
    device_by_id = {_value(device, "id"): device for device in devices}
    area_by_id = {_value(area, "id"): area for area in areas}

    domain_counts: Counter[str] = Counter()
    integration_counts: Counter[str] = Counter()
    area_counts: Counter[str] = Counter()
    unavailable: list[str] = []
    missing_area: list[str] = []
    disabled = 0
    enabled = 0

    for entry in entity_entries:
        entity_id = _value(entry, "entity_id")
        if not entity_id:
            continue
        domain = entity_id.split(".", 1)[0]
        domain_counts[domain] += 1

        platform = _value(entry, "platform", "unknown") or "unknown"
        integration_counts[platform] += 1

        is_disabled = _value(entry, "disabled_by") is not None
        if is_disabled:
            disabled += 1
            continue

        enabled += 1
        state = state_by_id.get(entity_id)
        if state is None or _value(state, "state") in (None, "unavailable", "unknown"):
            unavailable.append(entity_id)

        area_id = _value(entry, "area_id")
        if not area_id:
            device_id = _value(entry, "device_id")
            device = device_by_id.get(device_id)
            area_id = _value(device, "area_id") if device else None

        if area_id and area_id in area_by_id:
            area_counts[_value(area_by_id[area_id], "name", area_id)] += 1
        else:
            missing_area.append(entity_id)

    return {
        "entities": len([e for e in entity_entries if _value(e, "entity_id")]),
        "enabled_entities": enabled,
        "disabled_entities": disabled,
        "devices": len(devices),
        "areas": len(areas),
        "unavailable_entities": len(unavailable),
        "entities_without_area": len(missing_area),
        "by_domain": dict(sorted(domain_counts.items())),
        "by_integration": dict(sorted(integration_counts.items())),
        "by_area": dict(sorted(area_counts.items())),
        "unavailable": sorted(unavailable),
        "without_area": sorted(missing_area),
    }
