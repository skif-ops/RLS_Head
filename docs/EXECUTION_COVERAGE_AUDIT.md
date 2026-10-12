# Execution coverage audit

`tools.execution_coverage_audit` verifies that every evidence item declared
in `tools.measurement_readiness.PLAN` has all three workflow layers:

1. an external execution recipe;
2. a materializable `EXTERNAL-EVIDENCE-JOB-PACK-001`;
3. a non-null preflight state.

Unlike the external execution matrix, the coverage audit intentionally
includes dependency-blocked future items. This catches latent
`UNSUPPORTED` states before dependencies close.

Example:

```bash
python -m tools.execution_coverage_audit \
  --output-root outgoing/coverage_jobs \
  --output execution_coverage_audit.json
```

A `PASS` proves tooling coverage only. It does not mean any real
measurement, solver run, CAD review, simulation gate or physical antenna
evidence has passed.
