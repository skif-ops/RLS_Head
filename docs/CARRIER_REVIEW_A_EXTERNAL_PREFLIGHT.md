# System Carrier Review A external preflight

`tools.carrier_review_a_external_preflight` checks readiness to execute the
non-RF System Carrier KiCad Review A.

It requires the authoritative timing pinmap and BOM inputs to exist and pass
their existing consistency checks. It also requires Review A artifact slots,
ERC policy, explicit non-synthetic CAD_REVIEW provenance and all audit slots.

Before actual CAD execution, the KiCad schematic, ERC JSON and audit PASS
states may remain pending and are reported as warnings.

`READY_FOR_CAD_REVIEW_EXECUTION` is not Review A PASS and does not
authorize fabrication.
