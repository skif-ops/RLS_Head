#include "rls/targetstate_error_ledger.h"

#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define PI_F 3.14159265358979323846f
#define DEG_TO_RAD (PI_F / 180.0f)

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

static SysErrMat3f yaw_cov(float sigma_rad)
{
    SysErrMat3f out;
    memset(&out, 0, sizeof(out));
    out.m[8] = sigma_rad * sigma_rad;
    return out;
}

static bool build_reference_result(
    TargetStateSysErrResult *result)
{
    TargetStateV1 state;
    memset(&state, 0, sizeof(state));

    state.relative_position_m[0] = 300.0f;

    state.position_cov_ut[0] = 0.25f;
    state.position_cov_ut[3] = 0.04f;
    state.position_cov_ut[5] = 0.09f;

    TargetStateSysErrInputs inputs;
    memset(&inputs, 0, sizeof(inputs));

    inputs.host_attitude_cov_rad2 =
        yaw_cov(0.1f * DEG_TO_RAD);

    inputs.extrinsic_rotation_cov_rad2 =
        yaw_cov(0.03f * DEG_TO_RAD);

    inputs.angular_rate_rad_s.z = PI_F;
    inputs.timestamp_sigma_s = 0.0005f;

    return targetstate_apply_sys_err(
        &state,
        &inputs,
        result);
}

static bool test_ledger_001_reference(void)
{
    TargetStateSysErrResult result;

    CHECK(build_reference_result(&result));

    TargetStateErrorLedger ledger;

    CHECK(targetstate_build_error_ledger(
        &result,
        &ledger));

    CHECK(nearf_abs(
        ledger.base_trace_m2,
        0.38f,
        2.0e-6f));

    CHECK(nearf_abs(
        ledger.attitude_trace_m2,
        0.27415568f,
        3.0e-6f));

    CHECK(nearf_abs(
        ledger.timestamp_trace_m2,
        0.22206610f,
        3.0e-6f));

    CHECK(nearf_abs(
        ledger.extrinsic_trace_m2,
        0.024674011f,
        5.0e-7f));

    CHECK(nearf_abs(
        ledger.added_trace_m2,
        0.52089579f,
        5.0e-6f));

    CHECK(nearf_abs(
        ledger.total_trace_m2,
        0.90089579f,
        5.0e-6f));

    CHECK(
        ledger.dominant_overall_source ==
        TS_ERROR_SOURCE_BASE_TRACK);

    CHECK(
        ledger.dominant_added_source ==
        TS_ERROR_SOURCE_HOST_ATTITUDE);

    CHECK(nearf_abs(
        ledger.dominant_overall_fraction,
        0.42180239f,
        5.0e-6f));

    CHECK(nearf_abs(
        ledger.dominant_added_fraction,
        0.5263149f,
        5.0e-6f));

    CHECK(nearf_abs(
        ledger.base_fraction_total,
        0.42180239f,
        5.0e-6f));

    CHECK(nearf_abs(
        ledger.attitude_fraction_total,
        0.30431453f,
        5.0e-6f));

    CHECK(nearf_abs(
        ledger.timestamp_fraction_total,
        0.24649477f,
        5.0e-6f));

    CHECK(nearf_abs(
        ledger.extrinsic_fraction_total,
        0.02738831f,
        5.0e-6f));

    return true;
}

static bool test_ledger_002_names(void)
{
    CHECK(strcmp(
        targetstate_error_source_name(
            TS_ERROR_SOURCE_BASE_TRACK),
        "BASE_TRACK") == 0);

    CHECK(strcmp(
        targetstate_error_source_name(
            TS_ERROR_SOURCE_HOST_ATTITUDE),
        "HOST_ATTITUDE") == 0);

    CHECK(strcmp(
        targetstate_error_source_name(
            TS_ERROR_SOURCE_TIMESTAMP),
        "TIMESTAMP") == 0);

    CHECK(strcmp(
        targetstate_error_source_name(
            TS_ERROR_SOURCE_EXTRINSIC),
        "EXTRINSIC") == 0);

    return true;
}

static bool test_ledger_003_zero_added(void)
{
    TargetStateV1 state;
    memset(&state, 0, sizeof(state));

    state.relative_position_m[0] = 100.0f;
    state.position_cov_ut[0] = 0.25f;
    state.position_cov_ut[3] = 0.04f;
    state.position_cov_ut[5] = 0.09f;

    TargetStateSysErrInputs inputs;
    memset(&inputs, 0, sizeof(inputs));

    TargetStateSysErrResult result;

    CHECK(targetstate_apply_sys_err(
        &state,
        &inputs,
        &result));

    TargetStateErrorLedger ledger;

    CHECK(targetstate_build_error_ledger(
        &result,
        &ledger));

    CHECK(
        ledger.dominant_overall_source ==
        TS_ERROR_SOURCE_BASE_TRACK);

    CHECK(
        ledger.dominant_added_source ==
        TS_ERROR_SOURCE_NONE);

    CHECK(nearf_abs(
        ledger.dominant_overall_fraction,
        1.0f,
        1.0e-6f));

    return true;
}

static bool test_ledger_004_consistency_reject(void)
{
    TargetStateSysErrResult result;

    CHECK(build_reference_result(&result));

    result.total_position_cov_m2.m[0] += 1.0f;

    TargetStateErrorLedger ledger;

    CHECK(!targetstate_build_error_ledger(
        &result,
        &ledger));

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
        {"LEDGER-001 reference", test_ledger_001_reference},
        {"LEDGER-002 names", test_ledger_002_names},
        {"LEDGER-003 zero added", test_ledger_003_zero_added},
        {"LEDGER-004 consistency reject", test_ledger_004_consistency_reject}
    };

    const size_t count =
        sizeof(tests) / sizeof(tests[0]);

    for (size_t i = 0; i < count; ++i) {
        if (!tests[i].fn()) {
            fprintf(
                stderr,
                "%s FAILED\n",
                tests[i].name);

            return 1;
        }

        printf(
            "%s PASS\n",
            tests[i].name);
    }

    printf(
        "TARGETSTATE ERROR LEDGER SUITE PASS (%zu tests)\n",
        count);

    return 0;
}
