#include "rls/hil_r2_evidence.h"

#include <math.h>
#include <stdbool.h>
#include <stdio.h>

#define CHECK(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return false; \
    } \
} while (0)

static bool nearf_abs(
    float actual,
    float expected,
    float tolerance)
{
    return fabsf(actual - expected) <= tolerance;
}

static HilR2EvidenceGateConfig nominal_gate(void)
{
    HilR2EvidenceGateConfig cfg = {
        .min_radar_imu_samples = 4u,
        .min_pps_samples = 4u,

        .radar_imu_max_abs_us = 250.0f,
        .radar_imu_rms_us = 200.0f,

        .pps_max_abs_us = 100.0f,
        .pps_rms_us = 75.0f,

        .holdover_max_abs_us = 600.0f,

        .max_missed_events = 0u,
        .max_monotonic_failures = 0u
    };

    return cfg;
}

static bool test_stats_constant_bias(void)
{
    HilR2ResidualStats stats;
    hil_r2_residual_stats_reset(&stats);

    CHECK(hil_r2_residual_stats_push(&stats, 10.0f));
    CHECK(hil_r2_residual_stats_push(&stats, 10.0f));
    CHECK(hil_r2_residual_stats_push(&stats, 10.0f));
    CHECK(hil_r2_residual_stats_push(&stats, 10.0f));

    CHECK(stats.count == 4u);
    CHECK(nearf_abs((float)stats.mean_us, 10.0f, 1.0e-6f));
    CHECK(nearf_abs(stats.max_abs_us, 10.0f, 1.0e-6f));
    CHECK(nearf_abs(hil_r2_residual_stats_rms(&stats), 10.0f, 1.0e-6f));
    CHECK(nearf_abs(hil_r2_residual_stats_stddev(&stats), 0.0f, 1.0e-6f));

    return true;
}

static bool test_stats_symmetric(void)
{
    HilR2ResidualStats stats;
    hil_r2_residual_stats_reset(&stats);

    CHECK(hil_r2_residual_stats_push(&stats, -100.0f));
    CHECK(hil_r2_residual_stats_push(&stats, 100.0f));
    CHECK(hil_r2_residual_stats_push(&stats, -100.0f));
    CHECK(hil_r2_residual_stats_push(&stats, 100.0f));

    CHECK(nearf_abs((float)stats.mean_us, 0.0f, 1.0e-6f));
    CHECK(nearf_abs(hil_r2_residual_stats_rms(&stats), 100.0f, 1.0e-5f));
    CHECK(stats.min_us == -100.0f);
    CHECK(stats.max_us == 100.0f);

    return true;
}

static bool fill_nominal_evidence(
    HilR2Evidence *evidence)
{
    hil_r2_evidence_reset(evidence);

    const float radar_imu[] = {
        -100.0f,
        50.0f,
        120.0f,
        -80.0f
    };

    const float pps[] = {
        -20.0f,
        10.0f,
        30.0f,
        -10.0f
    };

    for (unsigned i = 0u; i < 4u; ++i) {
        CHECK(hil_r2_evidence_record_radar_imu(
            evidence,
            radar_imu[i]));

        CHECK(hil_r2_evidence_record_pps(
            evidence,
            pps[i]));
    }

    CHECK(hil_r2_evidence_update_holdover(
        evidence,
        120.0f));

    return true;
}

static bool test_gate_pass(void)
{
    HilR2Evidence evidence;
    CHECK(fill_nominal_evidence(&evidence));

    const HilR2EvidenceGateConfig cfg =
        nominal_gate();

    CHECK(hil_r2_evidence_evaluate(
        &evidence,
        &cfg) == HIL_R2_EVIDENCE_PASS);

    return true;
}

static bool test_gate_insufficient(void)
{
    HilR2Evidence evidence;
    hil_r2_evidence_reset(&evidence);

    const HilR2EvidenceGateConfig cfg =
        nominal_gate();

    CHECK(hil_r2_evidence_evaluate(
        &evidence,
        &cfg) == HIL_R2_EVIDENCE_INSUFFICIENT);

    return true;
}

static bool test_gate_radar_imu_fail(void)
{
    HilR2Evidence evidence;
    CHECK(fill_nominal_evidence(&evidence));

    CHECK(hil_r2_evidence_record_radar_imu(
        &evidence,
        400.0f));

    const HilR2EvidenceGateConfig cfg =
        nominal_gate();

    CHECK(hil_r2_evidence_evaluate(
        &evidence,
        &cfg) ==
        HIL_R2_EVIDENCE_RADAR_IMU_FAIL);

    return true;
}

static bool test_gate_pps_fail(void)
{
    HilR2Evidence evidence;
    CHECK(fill_nominal_evidence(&evidence));

    CHECK(hil_r2_evidence_record_pps(
        &evidence,
        150.0f));

    const HilR2EvidenceGateConfig cfg =
        nominal_gate();

    CHECK(hil_r2_evidence_evaluate(
        &evidence,
        &cfg) ==
        HIL_R2_EVIDENCE_PPS_FAIL);

    return true;
}

static bool test_gate_holdover_fail(void)
{
    HilR2Evidence evidence;
    CHECK(fill_nominal_evidence(&evidence));

    CHECK(hil_r2_evidence_update_holdover(
        &evidence,
        700.0f));

    const HilR2EvidenceGateConfig cfg =
        nominal_gate();

    CHECK(hil_r2_evidence_evaluate(
        &evidence,
        &cfg) ==
        HIL_R2_EVIDENCE_HOLDOVER_FAIL);

    return true;
}

static bool test_gate_capture_fail(void)
{
    HilR2Evidence evidence;
    CHECK(fill_nominal_evidence(&evidence));

    evidence.imu_drdy_missed = 1u;

    const HilR2EvidenceGateConfig cfg =
        nominal_gate();

    CHECK(hil_r2_evidence_evaluate(
        &evidence,
        &cfg) ==
        HIL_R2_EVIDENCE_CAPTURE_FAIL);

    return true;
}

static bool test_gate_monotonic_fail(void)
{
    HilR2Evidence evidence;
    CHECK(fill_nominal_evidence(&evidence));

    evidence.monotonic_failures = 1u;

    const HilR2EvidenceGateConfig cfg =
        nominal_gate();

    CHECK(hil_r2_evidence_evaluate(
        &evidence,
        &cfg) ==
        HIL_R2_EVIDENCE_TIME_FAIL);

    return true;
}

typedef bool (*TestFn)(void);

typedef struct {
    const char *name;
    TestFn fn;
} TestCase;

int main(void)
{
    const TestCase tests[] = {
        {"R2E-001 constant bias stats", test_stats_constant_bias},
        {"R2E-002 symmetric stats", test_stats_symmetric},
        {"R2E-003 gate pass", test_gate_pass},
        {"R2E-004 insufficient", test_gate_insufficient},
        {"R2E-005 Radar-IMU fail", test_gate_radar_imu_fail},
        {"R2E-006 PPS fail", test_gate_pps_fail},
        {"R2E-007 holdover fail", test_gate_holdover_fail},
        {"R2E-008 capture fail", test_gate_capture_fail},
        {"R2E-009 monotonic fail", test_gate_monotonic_fail}
    };

    const size_t count =
        sizeof(tests) / sizeof(tests[0]);

    for (size_t i = 0u; i < count; ++i) {
        if (!tests[i].fn()) {
            fprintf(stderr, "%s FAILED\n", tests[i].name);
            return 1;
        }

        printf("%s PASS\n", tests[i].name);
    }

    printf(
        "HIL-R2 EVIDENCE SUITE PASS (%zu tests)\n",
        count);

    return 0;
}
