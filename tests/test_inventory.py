from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
MODULE_PATH = Path(__file__).parents[1] / "custom_components" / "house_intelligence" / "inventory.py"
SPEC = spec_from_file_location("house_inventory", MODULE_PATH)
INVENTORY = module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)
build_inventory = INVENTORY.build_inventory

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
        ns(entity_id="sensor.living_temp", state="21.5", attributes={"device_class":"temperature","state_class":"measurement","unit_of_measurement":"°C"}),
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
        ns(entity_id="sensor.temp", platform="tuya", disabled_by=None, area_id=None, device_id=None),
    ]
    result = build_inventory(entities, [], [], [])
    assert result["unavailable_entities"] == 2
    assert result["entities_without_area"] == 2
    assert result["unavailable_by_integration"] == {"mqtt": 1, "tuya": 1}
    assert result["without_area_by_integration"] == {"mqtt": 1, "tuya": 1}

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
