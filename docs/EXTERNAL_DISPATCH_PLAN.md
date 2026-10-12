# External dispatch plan

`tools.external_dispatch_plan` adds an operational view on top of the
strategic external execution matrix.

The strategic queue is intentionally based on dependency-unlock value. That
can place a high-value item first even when its freshly generated job-pack is
still preflight `BLOCKED`.

The dispatch plan therefore groups work as:

- `DISPATCH_NOW` — preflight is already in a `READY_*` state;
- `WAITING_DEPENDENCY` — preflight reports a `WAITING_*` state;
- `PREP_REQUIRED` — preflight is `BLOCKED`;
- `UNKNOWN` — no recognized operational state.

Within each group it preserves dependency-unlock value and strategic
priority as tie-breakers.

This is read-only scheduling metadata. It does not change the authoritative
evidence manifest, the strategic queue, or any evidence status.

Usage:

```bash
python -m tools.external_dispatch_plan \
  external_execution_matrix.json \
  --output external_dispatch_plan.json
```
