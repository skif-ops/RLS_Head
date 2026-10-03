from tools.evidence_status import validate_manifest


def manifest():
    return {
        "schema": "PROJECT-EVIDENCE-MANIFEST-001",
        "items": [
            {
                "id": "A",
                "status": "PASS",
                "evidence_level": "SOFTWARE_CI",
                "synthetic": False,
                "requires_measured_evidence": False,
            },
            {
                "id": "B",
                "status": "OPEN",
                "evidence_level": "OPEN",
                "synthetic": False,
                "requires_measured_evidence": True,
            },
        ],
        "milestones": {
            "M": ["A", "B"],
        },
    }


def test_valid_manifest_with_open_milestone():
    result = validate_manifest(manifest())

    assert result["status"] == "VALID"
    assert result["milestones"]["M"]["status"] == "OPEN"
    assert result["milestones"]["M"]["open_items"] == ["B"]
    assert result["measured_open_items"] == ["B"]


def test_milestone_pass_when_all_pass():
    data = manifest()
    data["items"][1]["status"] = "PASS"
    data["items"][1]["evidence_level"] = "MEASURED_EVM"

    result = validate_manifest(data)

    assert result["status"] == "VALID"
    assert result["milestones"]["M"]["status"] == "PASS"


def test_synthetic_cannot_be_marked_measured():
    data = manifest()
    data["items"][0]["synthetic"] = True
    data["items"][0]["evidence_level"] = "MEASURED_FIELD"

    result = validate_manifest(data)

    assert result["status"] == "INVALID"
    assert "synthetic_marked_measured:A" in result["errors"]


def test_pass_requires_evidence_level():
    data = manifest()
    data["items"][0]["evidence_level"] = "OPEN"

    result = validate_manifest(data)

    assert result["status"] == "INVALID"
    assert "pass_without_evidence:A" in result["errors"]


def test_duplicate_id_invalid():
    data = manifest()
    data["items"].append(dict(data["items"][0]))

    result = validate_manifest(data)

    assert result["status"] == "INVALID"
    assert "duplicate_id:A" in result["errors"]
