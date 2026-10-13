import csv


def _rows(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_input_tvs_is_shunt_not_series():
    power = _rows(
        "hardware/system_carrier/POWER_TREE_SYS_001.csv"
    )

    tvs = next(
        row
        for row in power
        if row["device"] == "SMAJ15CA"
    )

    assert tvs["input_net"] == "VIN_RAW"
    assert tvs["output_net"] == "GND"
    assert tvs["setting"] == "SHUNT_TVS"

    efuse = next(
        row
        for row in power
        if row["device"] == "TPS259470ARPWR"
        and row["output_net"] == "VIN_PROTECTED"
    )

    assert efuse["input_net"] == "VIN_RAW"


def test_u6_input_uses_vin_raw():
    rows = _rows(
        "hardware/system_carrier/SYMBOL_PIN_CONTRACT_SYS_001.csv"
    )

    u6_in = next(
        row
        for row in rows
        if row["ref"] == "U6"
        and row["pin_number"] == "5"
    )

    assert u6_in["connection"] == "VIN_RAW"
