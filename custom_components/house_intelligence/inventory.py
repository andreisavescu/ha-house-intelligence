"""Pure inventory and current-state analysis helpers.

This module deliberately has no Home Assistant imports so it can be tested
independently and reused by future analysis modules.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

SAMPLE_LIMIT = 25
MEASUREMENT_STALE_AFTER = timedelta(hours=24)


def _value(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a mapping or an object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _sorted_counts(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def _as_utc(value: Any) -> datetime | None:
    """Normalize a datetime to UTC, returning None for unsupported values."""
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_state_analysis(
    entity_entries: list[Any],
    devices: list[Any],
    areas: list[Any],
    states: list[Any],
    *,
    now: datetime | None = None,
    stale_after: timedelta = MEASUREMENT_STALE_AFTER,
) -> dict[str, Any]:
    """Assess availability and freshness of registered measurement sensors.

    Only sensor entities explicitly classified as measurements are evaluated
    for freshness. This avoids treating slowly changing totals and arbitrary
    status entities as stale measurements.
    """
    current_time = _as_utc(now) or datetime.now(timezone.utc)
    state_by_id = {_value(state, "entity_id"): state for state in states}
    device_by_id = {_value(device, "id"): device for device in devices}
    area_by_id = {_value(area, "id"): area for area in areas}

    totals = Counter()
    by_area: dict[str, Counter[str]] = defaultdict(Counter)
    unavailable: list[str] = []
    stale: list[str] = []

    for entry in entity_entries:
        entity_id = _value(entry, "entity_id")
        if not entity_id or entity_id.split(".", 1)[0] != "sensor":
            continue

        state = state_by_id.get(entity_id)
        attributes = _value(state, "attributes", {}) or {}
        state_class = attributes.get("state_class") or _value(entry, "state_class")
        device_class = attributes.get("device_class") or _value(entry, "device_class")
        unit = attributes.get("unit_of_measurement") or _value(entry, "unit_of_measurement")
        if state_class not in ("measurement", "measurement_angle") and not (
            device_class and unit
        ):
            continue

        totals["total"] += 1
        device = device_by_id.get(_value(entry, "device_id"))
        area_id = _value(entry, "area_id") or _value(device, "area_id")
        area_name = (
            _value(area_by_id.get(area_id), "name", area_id)
            if area_id and area_id in area_by_id
            else "Unassigned"
        )
        area_counts = by_area[area_name]
        area_counts["total"] += 1

        state_value = _value(state, "state")
        if state is None or state_value in (None, "unknown", "unavailable"):
            totals["unavailable"] += 1
            area_counts["unavailable"] += 1
            unavailable.append(entity_id)
            continue

        # last_reported is preferable: it changes when an entity reports the
        # same value again. Older Home Assistant versions fall back to updated.
        reported_at = _as_utc(
            _value(state, "last_reported") or _value(state, "last_updated")
        )
        if reported_at is None:
            totals["unknown_age"] += 1
            area_counts["unknown_age"] += 1
            continue

        age = max(current_time - reported_at, timedelta(0))
        if age > stale_after:
            totals["stale"] += 1
            area_counts["stale"] += 1
            stale.append(entity_id)
        else:
            totals["fresh"] += 1
            area_counts["fresh"] += 1

    measurement_total = totals["total"]
    fresh_percent = (
        round((totals["fresh"] / measurement_total) * 100, 1)
        if measurement_total
        else None
    )
    unavailable.sort()
    stale.sort()

    return {
        "measurement_entities": measurement_total,
        "measurement_fresh": totals["fresh"],
        "measurement_unavailable": totals["unavailable"],
        "measurement_stale": totals["stale"],
        "measurement_unknown_age": totals["unknown_age"],
        "measurement_fresh_percent": fresh_percent,
        "measurement_stale_after_hours": stale_after.total_seconds() / 3600,
        "measurement_stale_sample": stale[:SAMPLE_LIMIT],
        "measurement_unavailable_sample": unavailable[:SAMPLE_LIMIT],
        "measurement_sample_limit": SAMPLE_LIMIT,
        "measurement_by_area": {
            name: dict(sorted(counts.items()))
            for name, counts in sorted(by_area.items())
        },
    }


def build_inventory(
    entity_entries: list[Any],
    devices: list[Any],
    areas: list[Any],
    states: list[Any],
    *,
    now: datetime | None = None,
    stale_after: timedelta = MEASUREMENT_STALE_AFTER,
) -> dict[str, Any]:
    """Build an inventory with bounded diagnostics and state analysis."""
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

    result = {
        "entities": len(valid_entries),
        "enabled_entities": enabled,
        "disabled_entities": disabled,
        "devices": len(devices),
        "areas": len(areas),
        "unavailable_entities": len(unavailable),
        "entities_without_area": len(missing_area),
        "entities_without_device": entities_without_device,
        "by_domain": _sorted_counts(domain_counts),
        "by_integration": _sorted_counts(integration_counts),
        "by_area": _sorted_counts(area_counts),
        "by_device_class": _sorted_counts(device_class_counts),
        "by_state_class": _sorted_counts(state_class_counts),
        "by_unit": _sorted_counts(unit_counts),
        "by_manufacturer": _sorted_counts(manufacturer_counts),
        "unavailable_by_integration": _sorted_counts(unavailable_by_integration),
        "without_area_by_integration": _sorted_counts(missing_area_by_integration),
        "unavailable_sample": unavailable[:SAMPLE_LIMIT],
        "without_area_sample": missing_area[:SAMPLE_LIMIT],
        "diagnostic_sample_limit": SAMPLE_LIMIT,
    }
    result.update(
        build_state_analysis(
            valid_entries, devices, areas, states, now=now, stale_after=stale_after
        )
    )
    return result
