#include "rls/targetstate_uncertainty.h"

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

    out.m[8] =
        sigma_rad * sigma_rad;

    return out;
}

static TargetStateV1 baseline_state(void)
{
    TargetStateV1 state;
    memset(&state, 0, sizeof(state));

    state.relative_position_m[0] = 300.0f;

    state.position_cov_ut[0] = 0.25f;
    state.position_cov_ut[3] = 0.04f;
    state.position_cov_ut[5] = 0.09f;

    state.timestamp_uncertainty_us = 10.0f;

    state.validity_mask =
        TS_VALID_POSITION |
        TS_VALID_VELOCITY |
        TS_VALID_POS_COV;

    return state;
}

static TargetStateSysErrInputs baseline_inputs(void)
{
    TargetStateSysErrInputs inputs;
    memset(&inputs, 0, sizeof(inputs));

    inputs.host_attitude_cov_rad2 =
        yaw_cov(
            0.1f * DEG_TO_RAD);

    inputs.extrinsic_rotation_cov_rad2 =
        yaw_cov(
            0.03f * DEG_TO_RAD);

    inputs.angular_rate_rad_s.z =
        PI_F;

    inputs.timestamp_sigma_s =
        0.0005f;

    return inputs;
}

static bool test_ts_syserr_001_combined_budget(void)
{
    TargetStateV1 state =
        baseline_state();

    const TargetStateSysErrInputs inputs =
        baseline_inputs();

    TargetStateSysErrResult result;

    CHECK(targetstate_apply_sys_err(
        &state,
        &inputs,
        &result));

    CHECK(nearf_abs(
        result.attitude_position_cov_m2.m[4],
        0.27415568f,
        3.0e-6f));

    CHECK(nearf_abs(
        result.timestamp_position_cov_m2.m[4],
        0.22206610f,
        3.0e-6f));

    CHECK(nearf_abs(
        result.extrinsic_position_cov_m2.m[4],
        0.024674011f,
        5.0e-7f));

    CHECK(nearf_abs(
        state.position_cov_ut[0],
        0.25f,
        1.0e-7f));

    CHECK(nearf_abs(
        state.position_cov_ut[3],
        0.5608958f,
        4.0e-6f));

    CHECK(nearf_abs(
        state.position_cov_ut[5],
        0.09f,
        1.0e-7f));

    CHECK(nearf_abs(
        result.added_position_rms_m,
        0.7217311f,
        4.0e-6f));

    CHECK(nearf_abs(
        result.total_position_rms_m,
        0.9491553f,
        4.0e-6f));

    CHECK(
        state.timestamp_uncertainty_us ==
        10.0f);

    return true;
}

static bool test_ts_syserr_002_zero_inputs_noop(void)
{
    TargetStateV1 state =
        baseline_state();

    TargetStateSysErrInputs inputs;
    memset(&inputs, 0, sizeof(inputs));

    TargetStateSysErrResult result;

    CHECK(targetstate_apply_sys_err(
        &state,
        &inputs,
        &result));

    CHECK(nearf_abs(
        state.position_cov_ut[0],
        0.25f,
        1.0e-7f));

    CHECK(nearf_abs(
        state.position_cov_ut[3],
        0.04f,
        1.0e-7f));

    CHECK(nearf_abs(
        state.position_cov_ut[5],
        0.09f,
        1.0e-7f));

    CHECK(nearf_abs(
        result.added_position_rms_m,
        0.0f,
        1.0e-7f));

    return true;
}

static bool test_ts_syserr_003_invalid_timestamp_sigma(void)
{
    TargetStateV1 state =
        baseline_state();

    TargetStateSysErrInputs inputs =
        baseline_inputs();

    inputs.timestamp_sigma_s =
        -0.001f;

    TargetStateSysErrResult result;

    CHECK(!targetstate_apply_sys_err(
        &state,
        &inputs,
        &result));

    CHECK(nearf_abs(
        state.position_cov_ut[3],
        0.04f,
        1.0e-7f));

    return true;
}

static bool test_ts_syserr_004_offdiagonal_preserved(void)
{
    TargetStateV1 state =
        baseline_state();

    state.position_cov_ut[1] = 0.01f;
    state.position_cov_ut[2] = -0.02f;
    state.position_cov_ut[4] = 0.03f;

    TargetStateSysErrInputs inputs;
    memset(&inputs, 0, sizeof(inputs));

    TargetStateSysErrResult result;

    CHECK(targetstate_apply_sys_err(
        &state,
        &inputs,
        &result));

    CHECK(nearf_abs(
        state.position_cov_ut[1],
        0.01f,
        1.0e-7f));

    CHECK(nearf_abs(
        state.position_cov_ut[2],
        -0.02f,
        1.0e-7f));

    CHECK(nearf_abs(
        state.position_cov_ut[4],
        0.03f,
        1.0e-7f));

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
        {"TS-SYSERR-001 combined", test_ts_syserr_001_combined_budget},
        {"TS-SYSERR-002 zero noop", test_ts_syserr_002_zero_inputs_noop},
        {"TS-SYSERR-003 invalid sigma", test_ts_syserr_003_invalid_timestamp_sigma},
        {"TS-SYSERR-004 offdiagonal", test_ts_syserr_004_offdiagonal_preserved}
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
        "TARGETSTATE SYS-ERR SUITE PASS (%zu tests)\n",
        count);

    return 0;
}
