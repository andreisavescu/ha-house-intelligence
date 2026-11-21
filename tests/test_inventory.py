from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

MODULE_PATH = Path(__file__).parents[1] / "custom_components" / "house_intelligence" / "inventory.py"
SPEC = spec_from_file_location("house_inventory", MODULE_PATH)
INVENTORY = module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)
build_inventory = INVENTORY.build_inventory
build_state_analysis = INVENTORY.build_state_analysis


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def test_inventory_counts_and_area_fallback():
    entities = [
        ns(entity_id="sensor.living_temp", platform="mqtt", disabled_by=None, area_id=None, device_id="dev1"),
        ns(entity_id="switch.garden", platform="tuya", disabled_by=None, area_id="area2", device_id=None),
        ns(entity_id="sensor.old", platform="mqtt", disabled_by="user", area_id=None, device_id=None),
    ]
    devices = [ns(id="dev1", area_id="area1", manufacturer="IKEA")]
    areas = [ns(id="area1", name="Living room"), ns(id="area2", name="Garden")]
    states = [
        ns(entity_id="sensor.living_temp", state="21.5", attributes={"device_class": "temperature", "state_class": "measurement", "unit_of_measurement": "°C"}),
        ns(entity_id="switch.garden", state="unavailable", attributes={}),
    ]
    result = build_inventory(entities, devices, areas, states)
    assert result["entities"] == 3
    assert result["enabled_entities"] == 2
    assert result["disabled_entities"] == 1
    assert result["unavailable_entities"] == 1
    assert result["entities_without_area"] == 0
    assert result["entities_without_device"] == 1
    assert result["by_area"] == {"Garden": 1, "Living room": 1}
    assert result["unavailable_by_integration"] == {"tuya": 1}
    assert result["by_device_class"] == {"temperature": 1}
    assert result["by_state_class"] == {"measurement": 1}
    assert result["by_unit"] == {"°C": 1}
    assert result["by_manufacturer"] == {"IKEA": 1}


def test_missing_state_and_area_are_grouped():
    entities = [
        ns(entity_id="binary_sensor.door", platform="mqtt", disabled_by=None, area_id=None, device_id=None),
        ns(entity_id="sensor.temp", platform="tuya", disabled_by=None, area_id=None, device_id=None, device_class="temperature", unit_of_measurement="°C"),
    ]
    result = build_inventory(entities, [], [], [])
    assert result["unavailable_entities"] == 2
    assert result["entities_without_area"] == 2
    assert result["unavailable_by_integration"] == {"mqtt": 1, "tuya": 1}
    assert result["without_area_by_integration"] == {"mqtt": 1, "tuya": 1}
    assert result["measurement_entities"] == 1
    assert result["measurement_unavailable"] == 1


def test_disabled_entities_are_not_quality_issues():
    entities = [ns(entity_id="sensor.disabled", platform="demo", disabled_by="integration", area_id=None, device_id=None)]
    result = build_inventory(entities, [], [], [])
    assert result["disabled_entities"] == 1
    assert result["unavailable_entities"] == 0
    assert result["entities_without_area"] == 0
    assert result["entities_without_device"] == 0


def test_diagnostic_samples_are_bounded():
    entities = [
        ns(entity_id=f"sensor.test_{index:02}", platform="demo", disabled_by=None, area_id=None, device_id=None)
        for index in range(40)
    ]
    result = build_inventory(entities, [], [], [])
    assert result["unavailable_entities"] == 40
    assert len(result["unavailable_sample"]) == INVENTORY.SAMPLE_LIMIT
    assert len(result["without_area_sample"]) == INVENTORY.SAMPLE_LIMIT


def test_measurement_freshness_uses_last_reported_and_area_fallback():
    now = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)
    entities = [
        ns(entity_id="sensor.living_temp", area_id=None, device_id="living_device", device_class="temperature", unit_of_measurement="°C"),
        ns(entity_id="sensor.old_temp", area_id="bedroom", device_id=None, device_class="temperature", unit_of_measurement="°C"),
        ns(entity_id="sensor.missing", area_id=None, device_id=None, device_class="humidity", unit_of_measurement="%"),
    ]
    devices = [ns(id="living_device", area_id="living", manufacturer="Test")]
    areas = [ns(id="living", name="Living room"), ns(id="bedroom", name="Bedroom")]
    states = [
        ns(entity_id="sensor.living_temp", state="21", attributes={"device_class": "temperature", "unit_of_measurement": "°C"}, last_reported=now - timedelta(minutes=5), last_updated=now - timedelta(days=2)),
        ns(entity_id="sensor.old_temp", state="19", attributes={"device_class": "temperature", "unit_of_measurement": "°C"}, last_reported=now - timedelta(hours=25), last_updated=now - timedelta(hours=25)),
    ]
    result = build_state_analysis(entities, devices, areas, states, now=now)
    assert result["measurement_entities"] == 3
    assert result["measurement_fresh"] == 1
    assert result["measurement_stale"] == 1
    assert result["measurement_unavailable"] == 1
    assert result["measurement_fresh_percent"] == 33.3
    assert result["measurement_by_area"]["Living room"]["fresh"] == 1
    assert result["measurement_by_area"]["Bedroom"]["stale"] == 1
    assert result["measurement_by_area"]["Unassigned"]["unavailable"] == 1


def test_measurement_age_falls_back_to_last_updated():
    now = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)
    entity = ns(entity_id="sensor.temp", device_class="temperature", unit_of_measurement="°C")
    state = ns(entity_id="sensor.temp", state="20", attributes={}, last_updated=now - timedelta(hours=1))
    result = build_state_analysis([entity], [], [], [state], now=now)
    assert result["measurement_fresh"] == 1
    assert result["measurement_unknown_age"] == 0


def test_non_measurement_totals_are_not_marked_stale():
    entity = ns(entity_id="sensor.energy_total", device_class="energy", unit_of_measurement="kWh")
    state = ns(entity_id="sensor.energy_total", state="123", attributes={"state_class": "total_increasing", "device_class": "energy", "unit_of_measurement": "kWh"}, last_reported=datetime(2026, 1, 1, tzinfo=timezone.utc))
    result = build_state_analysis([entity], [], [], [state], now=datetime(2026, 11, 21, tzinfo=timezone.utc))
    assert result["measurement_entities"] == 0
    assert result["measurement_fresh_percent"] is None
