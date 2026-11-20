from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "house_intelligence"
    / "inventory.py"
)
SPEC = spec_from_file_location("house_inventory", MODULE_PATH)
INVENTORY = module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)
build_inventory = INVENTORY.build_inventory


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def test_inventory_counts_and_area_fallback():
    entities = [
        ns(entity_id="sensor.living_temp", platform="mqtt", disabled_by=None,
           area_id=None, device_id="dev1"),
        ns(entity_id="switch.garden", platform="tuya", disabled_by=None,
           area_id="area2", device_id=None),
        ns(entity_id="sensor.old", platform="mqtt", disabled_by="user",
           area_id=None, device_id=None),
    ]
    devices = [ns(id="dev1", area_id="area1")]
    areas = [ns(id="area1", name="Living room"), ns(id="area2", name="Garden")]
    states = [ns(entity_id="sensor.living_temp", state="21.5"),
              ns(entity_id="switch.garden", state="unavailable")]

    result = build_inventory(entities, devices, areas, states)

    assert result["entities"] == 3
    assert result["enabled_entities"] == 2
    assert result["disabled_entities"] == 1
    assert result["devices"] == 1
    assert result["areas"] == 2
    assert result["unavailable_entities"] == 1
    assert result["entities_without_area"] == 0
    assert result["by_area"] == {"Garden": 1, "Living room": 1}
    assert result["by_integration"] == {"mqtt": 2, "tuya": 1}


def test_missing_state_and_area_are_reported():
    entities = [
        ns(entity_id="binary_sensor.front_door", platform="mqtt",
           disabled_by=None, area_id=None, device_id=None)
    ]
    result = build_inventory(entities, [], [], [])

    assert result["unavailable"] == ["binary_sensor.front_door"]
    assert result["without_area"] == ["binary_sensor.front_door"]
    assert result["unavailable_entities"] == 1
    assert result["entities_without_area"] == 1


def test_disabled_entities_are_not_marked_unavailable():
    entities = [
        ns(entity_id="sensor.disabled", platform="demo", disabled_by="integration",
           area_id=None, device_id=None)
    ]
    result = build_inventory(entities, [], [], [])

    assert result["disabled_entities"] == 1
    assert result["unavailable_entities"] == 0
    assert result["entities_without_area"] == 0
