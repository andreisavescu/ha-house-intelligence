# House Intelligence

A Home Assistant integration that builds a live inventory of the whole home and assesses the quality and freshness of its measurements.

## v0.2.0 — Current-state analysis

This release builds on the read-only discovery foundation. It evaluates registered measurement sensors, identifies unavailable and stale readings, and summarizes measurement freshness by area.

### Install with HACS

1. In HACS, open **Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/andreisavescu/ha-house-intelligence` as an **Integration**.
4. Install **House Intelligence** and restart Home Assistant.
5. Add the **House Intelligence** integration from Settings → Devices & services.

### Entities

The integration creates three diagnostic sensors:

- **Inventory** — totals for entities, enabled/disabled entities, devices and areas. Attributes break down the inventory by domain, integration, area, device class, state class, unit and device manufacturer. It also groups unavailable entities and missing area assignments by integration.
- **Data quality** — counts unavailable entities, entities without area assignments and stale measurements. It includes bounded examples and counts of measurements whose age cannot be established.
- **Measurement freshness** — percentage of registered measurement sensors with a recent reading. Attributes include fresh, stale, unavailable and unknown-age counts, plus a per-area breakdown.

### Measurement freshness semantics

- A measurement is a sensor with state class `measurement` or `measurement_angle`. If state class is absent, a sensor with both a device class and unit is treated as a measurement.
- Disabled entities and cumulative totals (for example, `total_increasing` energy meters) are excluded.
- A reading is stale after **24 hours** without a report.
- Home Assistant's `last_reported` timestamp is preferred because it advances even when a sensor reports the same value. `last_updated` is used as a compatibility fallback.
- Missing, `unknown` or `unavailable` states are counted separately. If no timestamp is available, the reading's age is reported as unknown.
- Freshness percentage is fresh measurements divided by all identified measurement entities. It is `unknown` when no measurement entities can be identified.
- Per-area results use entity area first, then the associated device's area. Sensors without either assignment are grouped under **Unassigned**.
- Example entity lists are capped at 25 to keep state attributes bounded.

The inventory refreshes every five minutes. The analysis is a snapshot of current Home Assistant state; it does not yet infer expected sensor coverage, occupancy, room relationships, energy flows or faults.

### Architecture

House Intelligence is an independent, read-only whole-home intelligence layer. Specialist integrations may contribute knowledge through their published Home Assistant entities and sensor attributes.

Heating Intelligence is one such specialist source. House Intelligence may consume its thermal measurements and derived insights, but it does not import its code, change its configuration, or require it to be installed. If Heating Intelligence is absent, House Intelligence continues to operate without that source.

### Design principles

- Read-only discovery and analysis.
- Keep specialist integrations independent.
- Consume published Home Assistant entities rather than coupling to another integration's implementation.
- Prefer a small number of useful summary entities over hundreds of generated entities.
- Build on Home Assistant registries and state data; do not require an external database or cloud service.
- Separate observed facts from inferred conclusions; do not claim coverage where no expected sensor inventory exists.

## Development

Run tests with:

```bash
python -m pytest
```
