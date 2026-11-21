# House Intelligence

A Home Assistant integration that builds a live inventory of the whole home and separates observed availability, measurement freshness, organization quality and entity classification.

## v0.3.0 — Entity classification and quality dimensions

This release adds deterministic entity classification and separates availability and organization diagnostics while preserving the existing v0.2.0 entities.

### Install with HACS

1. In HACS, open **Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/andreisavescu/ha-house-intelligence` as an **Integration**.
4. Install **House Intelligence** and restart Home Assistant.
5. Add the **House Intelligence** integration from Settings → Devices & services.

### Entities

The integration creates five diagnostic sensors:

- **Inventory** — totals for registered, enabled and disabled entities, devices and areas. Attributes include inventory breakdowns, entity classifications, unavailable entities by domain/integration/category, and actionable area-assignment metrics.
- **Data quality** — retains the v0.2.0 numeric state for dashboard compatibility. Its value is a legacy sum of unavailable entities, all entities without an area, and stale measurements. It is explicitly **not** a normalized health score. Attributes expose the separate dimensions.
- **Measurement freshness** — percentage of registered measurement sensors with a recent reading. Attributes include fresh, stale, unavailable and unknown-age counts, per-area results and per-category freshness.
- **Availability** — count of enabled entities currently unavailable, grouped by integration, domain and classification category. This is an observation, not a fault count: an entity may be intentionally or seasonally offline.
- **Organization** — count of entities missing an area assignment where a physical room/device area is applicable. Automations, helpers, derived calculations and specialist-derived entities are not treated as room-organization failures. The broader legacy missing-area count remains available on Inventory and Data quality.

### Entity classification

Classification uses Home Assistant entity domain, device class, state class, unit and integration platform. It is deterministic and does not use entity-name guessing.

Categories:

- **Environmental** — temperature, humidity, pressure, CO₂, particulate and weather-related measurements.
- **Energy/electrical** — power, energy, voltage, current and related electrical measurements.
- **Heating/cooling** — climate and heating/cooling controls, plus published Heating Intelligence outputs.
- **Presence/security** — doors, windows, motion, occupancy, cameras, locks and presence entities.
- **Device health** — battery, connectivity, firmware, problem and uptime entities.
- **Transport** — FordPass and vehicle integration entities.
- **Irrigation** — OpenSprinkler entities.
- **Infrastructure** — automations, scripts, helpers and control entities.
- **Other** — entities that do not match a more specific category.

Origin is tracked separately as device-backed, integration-provided, derived, or specialist-derived. Platforms such as Powercalc, Template, Integration, Min/Max, History Stats and Utility Meter are treated as derived sources. Heating Intelligence is treated as a specialist-derived source; House Intelligence consumes only its published Home Assistant entities and remains independent from its implementation.

### Measurement freshness semantics

- A measurement is a sensor with state class `measurement` or `measurement_angle`. If state class is absent, a sensor with both a device class and unit is treated as a measurement.
- Disabled entities and cumulative totals (for example, `total_increasing` energy meters) are excluded.
- A reading is stale after **24 hours** without a report.
- Home Assistant's `last_reported` timestamp is preferred because it advances even when a sensor reports the same value. `last_updated` is used as a compatibility fallback.
- Missing, `unknown` or `unavailable` states are counted separately. If no timestamp is available, the reading's age is reported as unknown.
- Freshness percentage is fresh measurements divided by all identified measurement entities. It is `unknown` when no measurement entities can be identified.
- Category-specific percentages help distinguish environmental, energy, device-health and other measurements.
- Per-area results use entity area first, then the associated device's area. Sensors without either assignment are grouped under **Unassigned**.
- Example entity lists are capped at 25 to keep state attributes bounded.

### Availability and seasonal operation

Availability reports the observed state of enabled entities. It does not infer that every unavailable entity is faulty or expected to be online. For example, an irrigation controller intentionally disconnected during winter remains visible as unavailable; it is not silently excluded or automatically labelled as a fault. User-configurable expected-online schedules and seasonal policies are future work.

### Organization semantics

The original all-entity missing-area count is retained for compatibility. The new Organization sensor narrows this to entities for which a physical area is meaningful, excluding automations, helpers, derived calculations and specialist-derived outputs. Whole-house calculations should not need to be assigned to a room.

The inventory refreshes every five minutes. Analysis is a snapshot of current Home Assistant state; it does not yet infer expected sensor coverage, occupancy, room relationships, energy flows or faults.

### Architecture and design principles

- Read-only discovery and analysis.
- Keep specialist integrations independent.
- Consume published Home Assistant entities rather than coupling to another integration's implementation.
- Prefer a small number of useful summary entities over hundreds of generated entities.
- Build on Home Assistant registries and state data; do not require an external database or cloud service.
- Separate observed facts from inferred conclusions.
- Never treat an unavailable entity as a fault without knowing whether it is expected to be online.

## Development

Run tests with:

```bash
python -m pytest
```
