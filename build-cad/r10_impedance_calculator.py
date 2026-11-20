from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


C0 = 299_792_458.0


def hammerstad_base_impedance(u: float) -> float:
    f_u = 6 + (2 * math.pi - 6) * math.exp(-((30.666 / u) ** 0.7528))
    return 60 * math.log(f_u / u + math.sqrt(1 + (2 / u) ** 2))


def hammerstad_effective_permittivity(u: float, er: float) -> float:
    a_u = (
        1
        + math.log((u**4 + (u / 52) ** 2) / (u**4 + 0.432)) / 49
        + math.log(1 + (u / 18.1) ** 3) / 18.7
    )
    b_er = 0.564 * ((er - 0.9) / (er + 3)) ** 0.053
    return (er + 1) / 2 + (er - 1) / 2 * (1 + 10 / u) ** (-a_u * b_er)


def microstrip(width_mm: float, height_mm: float, copper_mm: float, er: float) -> tuple[float, float]:
    u = width_mm / height_mm
    t_norm = copper_mm / height_mm
    if t_norm > 0:
        coth_term = 1 / math.tanh(math.sqrt(6.517 * u))
        du1 = t_norm / math.pi * math.log(1 + 4 * math.e / (t_norm * coth_term**2))
        dur = du1 * (1 + 1 / math.cosh(math.sqrt(er - 1))) / 2
    else:
        du1 = 0.0
        dur = 0.0
    u_for_er = u + du1
    u_for_z0 = u + dur
    eeff = hammerstad_effective_permittivity(u_for_er, er)
    z0 = hammerstad_base_impedance(u_for_z0) / math.sqrt(eeff)
    return z0, eeff


def differential_microstrip(
    width_mm: float,
    gap_mm: float,
    height_mm: float,
    copper_mm: float,
    er: float,
) -> tuple[float, float, float]:
    z0, eeff = microstrip(width_mm, height_mm, copper_mm, er)
    z_diff = 2 * z0 * (1 - 0.48 * math.exp(-0.96 * gap_mm / height_mm))
    return z_diff, z0, eeff


def solve_single(target_ohm: float, height_mm: float, copper_mm: float, er: float) -> float:
    low = 0.005
    high = 2.0
    for _ in range(100):
        mid = (low + high) / 2
        z0, _ = microstrip(mid, height_mm, copper_mm, er)
        if z0 > target_ohm:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def solve_differential(target_ohm: float, gap_mm: float, height_mm: float, copper_mm: float, er: float) -> float:
    low = 0.005
    high = 2.0
    for _ in range(100):
        mid = (low + high) / 2
        z_diff, _, _ = differential_microstrip(mid, gap_mm, height_mm, copper_mm, er)
        if z_diff > target_ohm:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def sensitivity_rows(
    profile: str,
    width_mm: float,
    height_mm: float,
    copper_mm: float,
    er: float,
    target_ohm: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cases = [
        ("nominal", width_mm, height_mm, copper_mm, er),
        ("etch_minus_0.015mm", width_mm - 0.015, height_mm, copper_mm, er),
        ("etch_plus_0.015mm", width_mm + 0.015, height_mm, copper_mm, er),
        ("dielectric_minus_10pct", width_mm, height_mm * 0.9, copper_mm, er),
        ("dielectric_plus_10pct", width_mm, height_mm * 1.1, copper_mm, er),
        ("dk_rld_3.03", width_mm, height_mm, copper_mm, 3.03),
        ("dk_ed_3.16", width_mm, height_mm, copper_mm, 3.16),
        ("finished_copper_33um", width_mm, height_mm, 0.033, er),
        ("finished_copper_15um", width_mm, height_mm, 0.015, er),
    ]
    for case, width, height, case_copper, case_er in cases:
        z0, eeff = microstrip(width, height, case_copper, case_er)
        rows.append(
            {
                "profile": profile,
                "case": case,
                "target_ohm": target_ohm,
                "width_mm": round(width, 5),
                "height_mm": round(height, 5),
                "copper_mm": case_copper,
                "er": round(case_er, 4),
                "calculated_ohm": round(z0, 3),
                "effective_er": round(eeff, 4),
                "deviation_pct": round((z0 / target_ohm - 1) * 100, 3),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def file_evidence(path: Path, repo: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(repo)).replace("\\", "/"),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest().upper(),
    }


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    release_dir = repo / "hardware" / "radar" / "altium" / "RADAR_D79_v0.9.0_R10_ENGINEERING_REWORK"
    output_dir = release_dir / "07_Расчеты_СВЧ"
    output_dir.mkdir(parents=True, exist_ok=True)

    rf_factory = {"height_mm": 0.127, "copper_mm": 0.045, "er": 3.16, "target_ohm": 50.0}
    rf_factory_width = solve_single(
        rf_factory["target_ohm"], rf_factory["height_mm"], rf_factory["copper_mm"], rf_factory["er"]
    )
    rf_factory_z0, rf_factory_eeff = microstrip(
        rf_factory_width, rf_factory["height_mm"], rf_factory["copper_mm"], rf_factory["er"]
    )

    rf_rld = {"height_mm": 0.127, "copper_mm": 0.015, "er": 3.03, "target_ohm": 50.0}
    rf_rld_width = solve_single(
        rf_rld["target_ohm"], rf_rld["height_mm"], rf_rld["copper_mm"], rf_rld["er"]
    )
    rf_rld_z0, rf_rld_eeff = microstrip(
        rf_rld_width, rf_rld["height_mm"], rf_rld["copper_mm"], rf_rld["er"]
    )

    fr4_inner = {"height_mm": 0.115, "copper_mm": 0.015, "er": 4.20}
    ro3003_outer = {"height_mm": 0.127, "copper_mm": 0.045, "er": 3.16}
    usb_gap = 0.150
    can_gap = 0.200

    clock_width = solve_single(50.0, **fr4_inner)
    clock_z0, clock_eeff = microstrip(clock_width, **fr4_inner)
    usb_inner_width = solve_differential(90.0, usb_gap, **fr4_inner)
    usb_inner_zdiff, usb_inner_z0, usb_inner_eeff = differential_microstrip(
        usb_inner_width, usb_gap, **fr4_inner
    )
    can_inner_width = solve_differential(120.0, can_gap, **fr4_inner)
    can_inner_zdiff, can_inner_z0, can_inner_eeff = differential_microstrip(
        can_inner_width, can_gap, **fr4_inner
    )
    usb_bottom_width = solve_differential(90.0, usb_gap, **ro3003_outer)
    usb_bottom_zdiff, usb_bottom_z0, usb_bottom_eeff = differential_microstrip(
        usb_bottom_width, usb_gap, **ro3003_outer
    )
    can_bottom_width = solve_differential(120.0, can_gap, **ro3003_outer)
    can_bottom_zdiff, can_bottom_z0, can_bottom_eeff = differential_microstrip(
        can_bottom_width, can_gap, **ro3003_outer
    )

    profiles = [
        {
            "profile": "RF50_FACTORY_ED45_L1_L2",
            "target_ohm": 50.0,
            "layer": "L1",
            "reference": "L2_RF_GND",
            "material": "RO3003G2, Rezonit published standard-process assumption",
            "design_er": 3.16,
            "height_mm": 0.127,
            "copper_mm": 0.045,
            "width_mm": round(rf_factory_width, 5),
            "gap_mm": "",
            "calculated_ohm": round(rf_factory_z0, 3),
            "effective_er": round(rf_factory_eeff, 4),
            "mask": "none",
            "topology": "open microstrip L1 over continuous L2 RF_GND",
            "method": "Hammerstad-Jensen with finite copper thickness correction",
            "status": "REZONIT_DOCUMENT_RECALC_FIELD_SOLVER_AND_COUPON_REQUIRED",
        },
        {
            "profile": "RF50_SPECIAL_RLD15_L1_L2",
            "target_ohm": 50.0,
            "layer": "L1",
            "reference": "L2_RF_GND",
            "material": "RO3003G2, special low-profile or rolled copper option",
            "design_er": 3.03,
            "height_mm": 0.127,
            "copper_mm": 0.015,
            "width_mm": round(rf_rld_width, 5),
            "gap_mm": "",
            "calculated_ohm": round(rf_rld_z0, 3),
            "effective_er": round(rf_rld_eeff, 4),
            "mask": "none",
            "topology": "open microstrip L1 over continuous L2 RF_GND",
            "method": "Hammerstad-Jensen cross-check against Rezonit 76 to 81 GHz article",
            "status": "ALTERNATIVE_ONLY_WRITTEN_FABRICATOR_CONFIRMATION_REQUIRED",
        },
        {
            "profile": "CLOCK50_L3_L2",
            "target_ohm": 50.0,
            "layer": "L3",
            "reference": "L2_RF_GND",
            "material": "FR-4 Tg150 nominal",
            "design_er": 4.20,
            "height_mm": 0.115,
            "copper_mm": 0.015,
            "width_mm": round(clock_width, 5),
            "gap_mm": "",
            "calculated_ohm": round(clock_z0, 3),
            "effective_er": round(clock_eeff, 4),
            "mask": "internal",
            "topology": "embedded asymmetric line between L2 and L4",
            "method": "screening estimate using the nearest reference plane; not an asymmetric-stripline solution",
            "status": "SCREENING_ONLY_FACTORY_STACK_AND_FIELD_SOLVER_REQUIRED",
        },
        {
            "profile": "USB90_L8_L9",
            "target_ohm": 90.0,
            "layer": "L8",
            "reference": "L9_DIGITAL_GND",
            "material": "FR-4 Tg150 nominal",
            "design_er": 4.20,
            "height_mm": 0.115,
            "copper_mm": 0.015,
            "width_mm": round(usb_inner_width, 5),
            "gap_mm": usb_gap,
            "calculated_ohm": round(usb_inner_zdiff, 3),
            "effective_er": round(usb_inner_eeff, 4),
            "mask": "internal",
            "topology": "embedded edge-coupled pair between L7 and L9",
            "method": "screening estimate using the nearest reference plane and closed-form coupling; not an asymmetric-stripline solution",
            "status": "SCREENING_ONLY_FACTORY_STACK_AND_FIELD_SOLVER_REQUIRED",
        },
        {
            "profile": "CAN120_L8_L9",
            "target_ohm": 120.0,
            "layer": "L8",
            "reference": "L9_DIGITAL_GND",
            "material": "FR-4 Tg150 nominal",
            "design_er": 4.20,
            "height_mm": 0.115,
            "copper_mm": 0.015,
            "width_mm": round(can_inner_width, 5),
            "gap_mm": can_gap,
            "calculated_ohm": round(can_inner_zdiff, 3),
            "effective_er": round(can_inner_eeff, 4),
            "mask": "internal",
            "topology": "embedded edge-coupled pair between L7 and L9",
            "method": "screening estimate using the nearest reference plane and closed-form coupling; not an asymmetric-stripline solution",
            "status": "SCREENING_ONLY_FACTORY_STACK_AND_FIELD_SOLVER_REQUIRED",
        },
        {
            "profile": "USB90_L10_L9",
            "target_ohm": 90.0,
            "layer": "L10",
            "reference": "L9_DIGITAL_GND",
            "material": "RO3003G2, Rezonit published standard-process assumption",
            "design_er": 3.16,
            "height_mm": 0.127,
            "copper_mm": 0.045,
            "width_mm": round(usb_bottom_width, 5),
            "gap_mm": usb_gap,
            "calculated_ohm": round(usb_bottom_zdiff, 3),
            "effective_er": round(usb_bottom_eeff, 4),
            "mask": "none in controlled segment",
            "topology": "bottom microstrip differential pair over continuous L9 DIGITAL_GND",
            "method": "Hammerstad-Jensen screening estimate with finite copper thickness and closed-form coupling",
            "status": "REZONIT_DOCUMENT_RECALC_FIELD_SOLVER_AND_COUPON_REQUIRED",
        },
        {
            "profile": "CAN120_L10_L9",
            "target_ohm": 120.0,
            "layer": "L10",
            "reference": "L9_DIGITAL_GND",
            "material": "RO3003G2, Rezonit published standard-process assumption",
            "design_er": 3.16,
            "height_mm": 0.127,
            "copper_mm": 0.045,
            "width_mm": round(can_bottom_width, 5),
            "gap_mm": can_gap,
            "calculated_ohm": round(can_bottom_zdiff, 3),
            "effective_er": round(can_bottom_eeff, 4),
            "mask": "none in controlled segment",
            "topology": "bottom microstrip differential pair over continuous L9 DIGITAL_GND",
            "method": "Hammerstad-Jensen screening estimate with finite copper thickness and closed-form coupling",
            "status": "REZONIT_DOCUMENT_RECALC_FIELD_SOLVER_AND_COUPON_REQUIRED",
        },
    ]

    sensitivity = sensitivity_rows(
        "RF50_FACTORY_ED45_L1_L2",
        rf_factory_width,
        rf_factory["height_mm"],
        rf_factory["copper_mm"],
        rf_factory["er"],
        rf_factory["target_ohm"],
    )

    wavelengths: list[dict[str, object]] = []
    for frequency_ghz in (76.0, 77.0, 78.5, 81.0):
        lambda0_mm = C0 / (frequency_ghz * 1e9) * 1000
        lambda_g_mm = lambda0_mm / math.sqrt(rf_factory_eeff)
        wavelengths.append(
            {
                "frequency_ghz": frequency_ghz,
                "lambda0_mm": round(lambda0_mm, 5),
                "lambda_g_mm": round(lambda_g_mm, 5),
                "quarter_wave_mm": round(lambda_g_mm / 4, 5),
            }
        )

    insertion_loss = [
        {
            "length_mm": length_mm,
            "datasheet_loss_db_per_in_at_77ghz": 1.3,
            "estimated_loss_db": round(1.3 * length_mm / 25.4, 4),
        }
        for length_mm in (5, 10, 20, 30)
    ]

    stackup = [
        {"item": "L1", "kind": "copper", "thickness_mm": 0.045, "material": "Готовая внешняя медь 45 мкм из базовой фольги 18 мкм по типовому процессу Резонита; обработку поверхности СВЧ подтвердить"},
        {"item": "D1", "kind": "dielectric", "thickness_mm": 0.127, "material": "RO3003G2, стандарт 5 mil"},
        {"item": "L2", "kind": "copper", "thickness_mm": 0.015, "material": "Готовая внутренняя медь 15 мкм из базовой фольги 18 мкм по типовому процессу Резонита"},
        {"item": "D2", "kind": "dielectric", "thickness_mm": 0.115, "material": "FR-4 Tg150, препрег 2116"},
        {"item": "L3", "kind": "copper", "thickness_mm": 0.015, "material": "Готовая внутренняя медь 15 мкм из базовой фольги 18 мкм по типовому процессу Резонита"},
        {"item": "D3", "kind": "dielectric", "thickness_mm": 0.100, "material": "FR-4 Tg150, ядро 0,100 мм из номенклатуры Резонита"},
        {"item": "L4", "kind": "copper", "thickness_mm": 0.015, "material": "Готовая внутренняя медь 15 мкм из базовой фольги 18 мкм по типовому процессу Резонита"},
        {"item": "D4", "kind": "dielectric", "thickness_mm": 0.255, "material": "FR-4 Tg150, препреги 2116 0,115 мм + 2116 0,140 мм; не менее 0,240 мм по правилу заполнения меди Резонита"},
        {"item": "L5", "kind": "copper", "thickness_mm": 0.105, "material": "Силовой слой PWR_A, медь 105 мкм; сохранен расчетный запас для 24 В"},
        {"item": "D5", "kind": "dielectric", "thickness_mm": 0.448, "material": "FR-4 Tg150, препреги 2116 0,115 мм + 2116 0,140 мм + 7628 0,193 мм; не менее 0,420 мм между слоями 105 мкм"},
        {"item": "L6", "kind": "copper", "thickness_mm": 0.105, "material": "Силовой слой PWR_B, медь 105 мкм; сохранен расчетный запас для 24 В"},
        {"item": "D6", "kind": "dielectric", "thickness_mm": 0.255, "material": "FR-4 Tg150, препреги 2116 0,115 мм + 2116 0,140 мм; не менее 0,240 мм по правилу заполнения меди Резонита"},
        {"item": "L7", "kind": "copper", "thickness_mm": 0.015, "material": "Готовая внутренняя медь 15 мкм из базовой фольги 18 мкм по типовому процессу Резонита"},
        {"item": "D7", "kind": "dielectric", "thickness_mm": 0.100, "material": "FR-4 Tg150, ядро 0,100 мм из номенклатуры Резонита"},
        {"item": "L8", "kind": "copper", "thickness_mm": 0.015, "material": "Готовая внутренняя медь 15 мкм из базовой фольги 18 мкм по типовому процессу Резонита"},
        {"item": "D8", "kind": "dielectric", "thickness_mm": 0.115, "material": "FR-4 Tg150, препрег 2116"},
        {"item": "L9", "kind": "copper", "thickness_mm": 0.015, "material": "Готовая внутренняя медь 15 мкм из базовой фольги 18 мкм по типовому процессу Резонита"},
        {"item": "D9", "kind": "dielectric", "thickness_mm": 0.127, "material": "RO3003G2, стандарт 5 mil"},
        {"item": "L10", "kind": "copper", "thickness_mm": 0.045, "material": "Готовая внешняя медь 45 мкм из базовой фольги 18 мкм по типовому процессу Резонита"},
    ]
    stack_total_mm = round(sum(float(row["thickness_mm"]) for row in stackup), 3)

    native_pcb = release_dir / "01_Исходник_Altium" / "RADAR_D79_POWER_24V_v0.9.3.37_R10_3_37_REZONIT_IMPEDANCE_RECALC_NATIVE.PcbDoc"
    drc_html = release_dir / "01_Исходник_Altium" / "Design Rule Check - RADAR_D79_POWER_24V_v0.9.3.html"
    drc_machine = release_dir / "01_Исходник_Altium" / "Design Rule Check - RADAR_D79_POWER_24V_v0.9.3.drc"
    routing_culture_report = release_dir / "05_DRC_и_аудит" / "R10_3_37" / "routing_culture_gate" / "R10_3_37_аудит_инженерной_культуры.json"
    routing_culture = json.loads(routing_culture_report.read_text(encoding="utf-8"))

    result = {
        "revision": "R10.3.37_REZONIT_DOCUMENT_RECALC",
        "source_checked_at": "2026-11-20",
        "production_authority": "NOT_AUTHORIZED",
        "material_source": "Rogers RO3003G2 data sheet",
        "material_source_url": "https://www.rogerscorp.com/-/media/project/rogerscorp/documents/advanced-electronics-solutions/english/data-sheets/ro3003g2--data-sheet.pdf",
        "material_data": {
            "process_dk_10ghz": "3.00 +/- 0.04",
            "design_dk_77ghz_g2": 3.07,
            "rezonit_article_rld_dk_76_81ghz": 3.03,
            "rezonit_article_ed_dk_76_81ghz": 3.16,
            "dissipation_factor_10ghz": 0.0011,
            "measured_insertion_loss_db_per_in_77ghz_5mil": 1.3,
            "standard_thickness": "0.005 in nominal; 0.127 mm exact conversion; Rogers table rounds to 0.13 mm",
            "copper": "Rezonit typical process values are 45 um finished external and 15 um finished signal/reference internal copper; PWR_A and PWR_B remain 105 um for the verified 24 V current screen",
            "solder_mask": "25 um, Dk 3.5; excluded from the controlled RF and bottom microstrip segments in this screening model",
        },
        "fabricator_source_url": "https://www.rezonit.ru/directory/v-pomoshch-konstruktoru/proektirovanie-elementov-konstrukcii-pechatnoj-platy-proizvodstva-v-rezonit/tipovye-sborki-i-konstruktsii-pechatnykh-plat/",
        "fabricator_impedance_source_url": "https://www.rezonit.ru/directory/v-pomoshch-konstruktoru/kontrol-volnovogo-soprotivleniya/bazovye-materialy-izmerennye-znacheniya/",
        "fabricator_copper_source_url": "https://www.rezonit.ru/directory/v-pomoshch-konstruktoru/kontrol-volnovogo-soprotivleniya/tolshchina-medi-dlya-raschetov/",
        "fabricator_order_source_url": "https://www.rezonit.ru/directory/v-pomoshch-konstruktoru/voprosy-i-otvety/kak-pravilno-ukazyvat-v-zakaze-trebovaniya-k-impedansu/",
        "fabricator_77ghz_article_url": "https://www.rezonit.ru/articles/analiz-vliyaniya-tekhnologicheskikh-parametrov-pechatnykh-plat-na-kharakteristiki-antennogo-elementa/",
        "fabricator_construction_rules_url": "https://www.rezonit.ru/directory/v-pomoshch-konstruktoru/proektirovanie-elementov-konstrukcii-pechatnoj-platy-proizvodstva-v-rezonit/rekomendatsii-k-elementam-konstruktsii/",
        "target_finished_thickness_mm": 2.00,
        "nominal_stack_thickness_before_mask_finish_mm": stack_total_mm,
        "native_validation": {
            "native_pcbdoc": file_evidence(native_pcb, repo),
            "drc_html": file_evidence(drc_html, repo),
            "drc_machine_report": file_evidence(drc_machine, repo),
            "warnings": 0,
            "rule_violations": 0,
            "unrouted_net_violations": 0,
            "polygon_repour_saved": True,
        },
        "routing_culture_validation": {
            "report": file_evidence(routing_culture_report, repo),
            "gate": routing_culture["gate"],
            "counts": routing_culture["counts"],
            "interpretation": "The strict geometric gate is not closed. DRC 0 does not establish complete GOST, IPC or engineering-culture conformity.",
        },
        "stackup": stackup,
        "profiles": profiles,
        "rf_sensitivity": sensitivity,
        "guided_wavelengths": wavelengths,
        "insertion_loss_length_estimate": insertion_loss,
        "r10_3_37_rf_routing_observation": {
            "rf_nets": ["TI_RX1", "TI_RX2", "TI_RX3", "TI_RX4", "TI_TX1", "TI_TX2", "TI_TX3", "TI_TX4"],
            "layers": ["TOP"],
            "observed_width_groups_mm": [0.10160, 0.21336, 0.21340],
            "non_gnd_vias_penetrating_L2_within_0_30_mm": 0,
            "interpretation": "The observed antenna feed widths are synthesized array sections. They must be mapped to the EM model before any width is replaced by the RF50 screening value.",
        },
        "limitations": [
            "The formulas are closed-form engineering estimates, not a 2D or 3D field solver.",
            "The internal CLOCK50, USB90 and CAN120 calculations use a nearest-plane screening approximation. Their real embedded asymmetric-stripline geometry requires the fabricator field solver.",
            "The differential formula is suitable for screening only and must not be released as production geometry.",
            "FR-4 Dk 4.20 is a screening assumption. The fabricator published value may be specified at 1 MHz and is not sufficient for final USB or CAN field solving.",
            "The nominal material sum is about 2.03 mm before mask and finish. The order target remains 2.00 mm and the fabricator must finalize the pressed construction within its published finished-board tolerance.",
            "The D4, D5 and D6 prepreg packages were increased so that the published Rezonit copper-fill rule is met around the 105 um power foils.",
            "Final dimensions require the fabricator stack, copper etch model, roughness model and impedance coupon.",
            "Antenna series-feed sections are synthesized impedances and must not be replaced by the RF50 profile.",
            "The RF50_FACTORY_ED45 profile is a conservative document-based process assumption, not permission to change every antenna track to one width.",
            "Public Rezonit data does not confirm procurement or processing of this exact ten-layer RO3003G2 hybrid stack. Written fabricator confirmation remains mandatory.",
            "The strict routing-culture gate is FAIL. Its findings require contextual review and correction before routing can be declared complete.",
        ],
    }

    write_csv(output_dir / "R10_профили_импеданса.csv", profiles)
    write_csv(output_dir / "R10_производственный_стек.csv", stackup)
    write_csv(output_dir / "R10_чувствительность_RF50.csv", sensitivity)
    write_csv(output_dir / "R10_направленная_длина_волны.csv", wavelengths)
    write_csv(output_dir / "R10_оценка_потерь_RO3003G2.csv", insertion_loss)
    (output_dir / "R10_расчет_импеданса.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
