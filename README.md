# House Intelligence

A Home Assistant integration that builds a live inventory of the whole home as the foundation for deeper analysis.

## v0.1.0 — Discovery foundation

This first release is deliberately read-only. It discovers registered entities, devices and areas, checks current availability, and exposes a compact inventory summary. It does not change devices, automations, helpers, or existing integrations.

### Install with HACS

1. In HACS, open **Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/andreisavescu/ha-house-intelligence` as an **Integration**.
4. Install **House Intelligence** and restart Home Assistant.
5. Add the **House Intelligence** integration from Settings → Devices & services.

### Entities

The integration creates two diagnostic sensors:

- **Inventory** — totals for entities, enabled/disabled entities, devices and areas. Attributes contain breakdowns by domain, integration and area.
- **Data quality** — counts of enabled entities that are unavailable and entities without an area assignment.

The inventory refreshes every five minutes.

### Design principles

- Read-only discovery first.
- Keep Heating Intelligence independent.
- Prefer a small number of useful summary entities over hundreds of generated entities.
- Build on Home Assistant registries and state data; do not require an external database or cloud service.

### Scope and limitations

This release is an inventory baseline, not yet a learning or prediction engine. It does not infer occupancy, energy flows, room relationships or faults. Those require additional validated data and will be introduced incrementally.

## Development

Run tests with:

```bash
python -m pytest
```
