#include "rls/sys_err.h"

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

static SysErrMat3f diag3(
    float x,
    float y,
    float z)
{
    SysErrMat3f out;
    memset(&out, 0, sizeof(out));

    out.m[0] = x;
    out.m[4] = y;
    out.m[8] = z;

    return out;
}

static bool test_sys_err_001_attitude_yaw(void)
{
    const HilR2Vec3f position = {
        100.0f,
        0.0f,
        0.0f
    };

    const float sigma_yaw =
        0.1f * DEG_TO_RAD;

    const SysErrMat3f attitude_cov =
        diag3(
            0.0f,
            0.0f,
            sigma_yaw * sigma_yaw);

    SysErrMat3f position_cov;

    CHECK(sys_err_small_angle_position_covariance(
        position,
        &attitude_cov,
        &position_cov));

    CHECK(nearf_abs(
        position_cov.m[4],
        0.030461742f,
        2.0e-7f));

    CHECK(nearf_abs(
        position_cov.m[0],
        0.0f,
        1.0e-8f));

    return true;
}

static bool test_sys_err_002_timestamp_rotation(void)
{
    const HilR2Vec3f position = {
        300.0f,
        0.0f,
        0.0f
    };

    const HilR2Vec3f relative_velocity = {
        0.0f,
        0.0f,
        0.0f
    };

    const HilR2Vec3f angular_rate = {
        0.0f,
        0.0f,
        PI_F
    };

    SysErrMat3f timing_cov;

    CHECK(sys_err_timing_position_covariance(
        position,
        relative_velocity,
        angular_rate,
        0.0005f,
        &timing_cov));

    CHECK(nearf_abs(
        timing_cov.m[4],
        0.22206610f,
        2.0e-6f));

    CHECK(nearf_abs(
        sqrtf(timing_cov.m[4]),
        0.4712389f,
        2.0e-6f));

    return true;
}

static bool test_sys_err_003_extrinsic_yaw(void)
{
    const HilR2Vec3f position = {
        300.0f,
        0.0f,
        0.0f
    };

    const float sigma_yaw =
        0.03f * DEG_TO_RAD;

    const SysErrMat3f extrinsic_cov =
        diag3(
            0.0f,
            0.0f,
            sigma_yaw * sigma_yaw);

    SysErrMat3f position_cov;

    CHECK(sys_err_small_angle_position_covariance(
        position,
        &extrinsic_cov,
        &position_cov));

    CHECK(nearf_abs(
        position_cov.m[4],
        0.024674011f,
        3.0e-7f));

    return true;
}

static bool test_sys_err_004_covariance_add(void)
{
    const SysErrMat3f a =
        diag3(
            0.25f,
            0.04f,
            0.09f);

    const SysErrMat3f b =
        diag3(
            0.01f,
            0.02f,
            0.03f);

    SysErrMat3f total;

    CHECK(sys_err_covariance_add(
        &a,
        &b,
        &total));

    CHECK(nearf_abs(total.m[0], 0.26f, 1.0e-7f));
    CHECK(nearf_abs(total.m[4], 0.06f, 1.0e-7f));
    CHECK(nearf_abs(total.m[8], 0.12f, 1.0e-7f));

    return true;
}

static bool test_sys_err_005_position_rms(void)
{
    const SysErrMat3f cov =
        diag3(
            0.25f,
            0.04f,
            0.09f);

    CHECK(nearf_abs(
        sys_err_position_rms(&cov),
        0.6164414f,
        2.0e-7f));

    return true;
}

static bool test_sys_err_006_invalid_sigma(void)
{
    SysErrMat3f out;

    CHECK(!sys_err_timing_position_covariance(
        (HilR2Vec3f){1.0f, 0.0f, 0.0f},
        (HilR2Vec3f){0.0f, 0.0f, 0.0f},
        (HilR2Vec3f){0.0f, 0.0f, 1.0f},
        -1.0f,
        &out));

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
        {"SYSERR-001 attitude yaw", test_sys_err_001_attitude_yaw},
        {"SYSERR-002 timestamp rotation", test_sys_err_002_timestamp_rotation},
        {"SYSERR-003 extrinsic yaw", test_sys_err_003_extrinsic_yaw},
        {"SYSERR-004 covariance add", test_sys_err_004_covariance_add},
        {"SYSERR-005 position RMS", test_sys_err_005_position_rms},
        {"SYSERR-006 invalid sigma", test_sys_err_006_invalid_sigma}
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
        "SYS-ERR COVARIANCE SUITE PASS (%zu tests)\n",
        count);

    return 0;
}
