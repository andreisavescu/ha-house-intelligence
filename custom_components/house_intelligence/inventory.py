"""Pure inventory, entity classification, and current-state analysis.

This module deliberately has no Home Assistant imports so it can be tested
independently and reused by future analysis modules.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

SAMPLE_LIMIT = 25
MEASUREMENT_STALE_AFTER = timedelta(hours=24)

DERIVED_PLATFORMS = {
    "history_stats",
    "integration",
    "min_max",
    "powercalc",
    "statistics",
    "template",
    "utility_meter",
}
SPECIALIST_PLATFORMS = {"heating_intelligence"}
PHYSICAL_AREA_DOMAINS = {
    "alarm_control_panel",
    "binary_sensor",
    "camera",
    "climate",
    "cover",
    "fan",
    "humidifier",
    "light",
    "lock",
    "media_player",
    "sensor",
    "switch",
    "vacuum",
    "water_heater",
}
ENVIRONMENTAL_CLASSES = {
    "aqi", "atmospheric_pressure", "carbon_dioxide", "conductivity",
    "humidity", "illuminance", "irradiance", "moisture", "pm10", "pm25",
    "precipitation", "precipitation_intensity", "pressure", "temperature",
    "volatile_organic_compounds", "volatile_organic_compounds_parts",
    "wind_direction", "wind_speed",
}
ENERGY_CLASSES = {
    "current", "energy", "energy_storage", "frequency", "gas", "heat",
    "monetary", "power", "power_factor", "voltage", "volume", "volume_flow_rate",
}
DEVICE_HEALTH_CLASSES = {
    "battery", "connectivity", "firmware", "problem", "signal_strength",
    "update", "uptime",
}
PRESENCE_CLASSES = {
    "door", "garage_door", "motion", "occupancy", "opening", "presence",
    "smoke", "sound", "vibration", "window",
}
DERIVED_AREA_EXEMPT_PLATFORMS = DERIVED_PLATFORMS | SPECIALIST_PLATFORMS


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


def classify_entity(entry: Any, state: Any = None) -> dict[str, str]:
    """Classify an entity using stable registry and state metadata.

    The category describes the entity's role; origin describes whether it is
    device-backed, derived, specialist-derived, or supplied by another source.
    """
    entity_id = _value(entry, "entity_id", "") or ""
    domain = entity_id.split(".", 1)[0]
    platform = str(_value(entry, "platform") or "unknown")
    attributes = _value(state, "attributes", {}) or {}
    device_class = (
        attributes.get("device_class")
        or _value(entry, "device_class")
        or ""
    )
    unit = (
        attributes.get("unit_of_measurement")
        or _value(entry, "unit_of_measurement")
        or ""
    )
    state_class = attributes.get("state_class") or _value(entry, "state_class")

    if platform in SPECIALIST_PLATFORMS:
        category = "heating_cooling"
        origin = "specialist_derived"
    elif platform == "opensprinkler":
        category = "irrigation"
        origin = "integration"
    elif platform in {"fordpass", "vehicule"}:
        category = "transport"
        origin = "integration"
    elif device_class in DEVICE_HEALTH_CLASSES:
        category = "device_health"
        origin = "device" if _value(entry, "device_id") else "integration"
    elif device_class in ENVIRONMENTAL_CLASSES:
        category = "environmental"
        origin = "derived" if platform in DERIVED_PLATFORMS else (
            "device" if _value(entry, "device_id") else "integration"
        )
    elif device_class in ENERGY_CLASSES or unit in {
        "W", "kW", "Wh", "kWh", "A", "mA", "V", "mV", "Hz"
    }:
        category = "energy_electrical"
        origin = "derived" if platform in DERIVED_PLATFORMS else (
            "device" if _value(entry, "device_id") else "integration"
        )
    elif device_class in PRESENCE_CLASSES or domain in {
        "alarm_control_panel", "camera", "device_tracker", "lock", "person"
    }:
        category = "presence_security"
        origin = "derived" if platform in DERIVED_PLATFORMS else (
            "device" if _value(entry, "device_id") else "integration"
        )
    elif domain in {"climate", "fan", "humidifier", "water_heater"} or device_class in {
        "dehumidifier", "heat"
    }:
        category = "heating_cooling"
        origin = "derived" if platform in DERIVED_PLATFORMS else (
            "device" if _value(entry, "device_id") else "integration"
        )
    elif domain in {
        "automation", "button", "counter", "input_boolean", "input_button",
        "input_datetime", "input_number", "input_select", "number", "script",
        "select", "switch", "text", "time", "timer", "update",
    }:
        category = "infrastructure"
        origin = "derived" if platform in DERIVED_PLATFORMS else (
            "device" if _value(entry, "device_id") else "integration"
        )
    elif platform in DERIVED_PLATFORMS:
        category = "other"
        origin = "derived"
    else:
        category = "other"
        origin = "device" if _value(entry, "device_id") else "integration"

    if platform in SPECIALIST_PLATFORMS:
        origin = "specialist_derived"

    return {
        "category": category,
        "origin": origin,
        "domain": domain or "unknown",
        "platform": platform,
        "device_class": str(device_class) if device_class else "",
        "state_class": str(state_class) if state_class else "",
        "unit": str(unit) if unit else "",
    }


def _area_assignment_expected(entry: Any, classification: dict[str, str]) -> bool:
    """Whether a physical room/device area is normally meaningful."""
    return (
        classification["domain"] in PHYSICAL_AREA_DOMAINS
        and classification["origin"] not in {"derived", "specialist_derived"}
    )


def build_state_analysis(
    entity_entries: list[Any],
    devices: list[Any],
    areas: list[Any],
    states: list[Any],
    *,
    now: datetime | None = None,
    stale_after: timedelta = MEASUREMENT_STALE_AFTER,
) -> dict[str, Any]:
    """Assess availability and freshness of registered measurement sensors."""
    current_time = _as_utc(now) or datetime.now(timezone.utc)
    state_by_id = {_value(state, "entity_id"): state for state in states}
    device_by_id = {_value(device, "id"): device for device in devices}
    area_by_id = {_value(area, "id"): area for area in areas}

    totals = Counter()
    by_area: dict[str, Counter[str]] = defaultdict(Counter)
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    unavailable: list[str] = []
    stale: list[str] = []

    for entry in entity_entries:
        entity_id = _value(entry, "entity_id")
        if (
            not entity_id
            or entity_id.split(".", 1)[0] != "sensor"
            or _value(entry, "disabled_by") is not None
        ):
            continue

        state = state_by_id.get(entity_id)
        attributes = _value(state, "attributes", {}) or {}
        state_class = attributes.get("state_class") or _value(entry, "state_class")
        device_class = attributes.get("device_class") or _value(entry, "device_class")
        unit = attributes.get("unit_of_measurement") or _value(entry, "unit_of_measurement")
        if state_class is not None:
            if state_class not in ("measurement", "measurement_angle"):
                continue
        elif not (device_class and unit):
            continue

        classification = classify_entity(entry, state)
        category = classification["category"]
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
        category_counts = by_category[category]
        category_counts["total"] += 1

        state_value = _value(state, "state")
        if state is None or state_value in (None, "unknown", "unavailable"):
            totals["unavailable"] += 1
            area_counts["unavailable"] += 1
            category_counts["unavailable"] += 1
            unavailable.append(entity_id)
            continue

        reported_at = _as_utc(
            _value(state, "last_reported") or _value(state, "last_updated")
        )
        if reported_at is None:
            totals["unknown_age"] += 1
            area_counts["unknown_age"] += 1
            category_counts["unknown_age"] += 1
            continue

        age = max(current_time - reported_at, timedelta(0))
        if age > stale_after:
            totals["stale"] += 1
            area_counts["stale"] += 1
            category_counts["stale"] += 1
            stale.append(entity_id)
        else:
            totals["fresh"] += 1
            area_counts["fresh"] += 1
            category_counts["fresh"] += 1

    measurement_total = totals["total"]
    fresh_percent = (
        round((totals["fresh"] / measurement_total) * 100, 1)
        if measurement_total else None
    )
    unavailable.sort()
    stale.sort()

    category_result = {}
    for name, counts in sorted(by_category.items()):
        total = counts["total"]
        category_result[name] = {
            **dict(sorted(counts.items())),
            "fresh_percent": round(counts["fresh"] / total * 100, 1) if total else None,
        }

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
        "measurement_by_category": category_result,
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
    """Build inventory, classification, availability and organization metrics."""
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
    unavailable_by_domain: Counter[str] = Counter()
    unavailable_by_category: Counter[str] = Counter()
    missing_area_by_integration: Counter[str] = Counter()
    missing_area_applicable_by_integration: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    origin_counts: Counter[str] = Counter()
    unavailable: list[str] = []
    missing_area: list[str] = []
    missing_area_applicable: list[str] = []
    enabled = disabled = entities_without_device = 0
    area_applicable = 0

    for entry in valid_entries:
        entity_id = _value(entry, "entity_id")
        domain = entity_id.split(".", 1)[0]
        integration = _value(entry, "platform") or "unknown"
        domain_counts[domain] += 1
        integration_counts[integration] += 1
        if _value(entry, "disabled_by") is not None:
            disabled += 1
            continue

        enabled += 1
        state = state_by_id.get(entity_id)
        classification = classify_entity(entry, state)
        category = classification["category"]
        classification_counts[category] += 1
        origin_counts[classification["origin"]] += 1

        if state is None or _value(state, "state") in (None, "unavailable", "unknown"):
            unavailable.append(entity_id)
            unavailable_by_integration[integration] += 1
            unavailable_by_domain[domain] += 1
            unavailable_by_category[category] += 1

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
        has_area = bool(area_id and area_id in area_by_id)
        if has_area:
            area_counts[_value(area_by_id[area_id], "name", area_id)] += 1
        else:
            missing_area.append(entity_id)
            missing_area_by_integration[integration] += 1

        if _area_assignment_expected(entry, classification):
            area_applicable += 1
            if not has_area:
                missing_area_applicable.append(entity_id)
                missing_area_applicable_by_integration[integration] += 1

    for device in devices:
        manufacturer = _value(device, "manufacturer")
        if manufacturer:
            manufacturer_counts[str(manufacturer)] += 1

    unavailable.sort()
    missing_area.sort()
    missing_area_applicable.sort()

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
        "unavailable_by_domain": _sorted_counts(unavailable_by_domain),
        "unavailable_by_category": _sorted_counts(unavailable_by_category),
        "without_area_by_integration": _sorted_counts(missing_area_by_integration),
        "area_assignment_applicable": area_applicable,
        "entities_missing_area_applicable": len(missing_area_applicable),
        "area_not_applicable_entities": enabled - area_applicable,
        "without_area_applicable_by_integration": _sorted_counts(
            missing_area_applicable_by_integration
        ),
        "without_area_applicable_sample": missing_area_applicable[:SAMPLE_LIMIT],
        "classification_by_category": _sorted_counts(classification_counts),
        "classification_by_origin": _sorted_counts(origin_counts),
        "classification_sample_limit": SAMPLE_LIMIT,
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
