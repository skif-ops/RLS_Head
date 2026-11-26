from pathlib import Path

from tools.carrier_review_a import REQUIRED_AUDITS
from tools.carrier_review_a_package import derive_audits


def test_current_contracts_cover_every_review_a_audit():
    audits, details = derive_audits(
        Path("hardware/system_carrier")
    )

    assert set(audits) == REQUIRED_AUDITS
    assert all(value == "PASS" for value in audits.values())
    assert details["checks"]["external_gnss"] is True
    assert details["checks"]["no_obsolete_interfaces"] is True
