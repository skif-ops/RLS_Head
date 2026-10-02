#include "rls/hil_r2.h"

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

static bool nearf_abs(float actual, float expected, float tolerance)
{
    return fabsf(actual - expected) <= tolerance;
}

static HilR2Quatf yaw_quat(float yaw_rad)
{
    const float half = 0.5f * yaw_rad;

    const HilR2Quatf q = {
        cosf(half),
        0.0f,
        0.0f,
        sinf(half)
    };

    return q;
}

static float vec_distance(HilR2Vec3f a, HilR2Vec3f b)
{
    const float dx = a.x - b.x;
    const float dy = a.y - b.y;
    const float dz = a.z - b.z;

    return sqrtf(dx * dx + dy * dy + dz * dz);
}

static bool test_r2_001_yaw_interpolation_5ms(void)
{
    HilR2HostSample a;
    HilR2HostSample b;
    HilR2HostSample out;

    memset(&a, 0, sizeof(a));
    memset(&b, 0, sizeof(b));

    a.timestamp_us = 0u;
    b.timestamp_us = 1000000u;

    a.q_nav_body = yaw_quat(0.0f);
    b.q_nav_body = yaw_quat(90.0f * DEG_TO_RAD);

    a.angular_rate_body_rad_s.z = 90.0f * DEG_TO_RAD;
    b.angular_rate_body_rad_s.z = 90.0f * DEG_TO_RAD;

    CHECK(hil_r2_host_state_interpolate(
        &a,
        &b,
        5000u,
        &out));

    CHECK(nearf_abs(out.q_nav_body.w, 0.9999922894f, 2.0e-6f));
    CHECK(nearf_abs(out.q_nav_body.z, 0.0039269807f, 2.0e-6f));

    const HilR2Vec3f p_body = {100.0f, 0.0f, 0.0f};
    HilR2Vec3f p_interp;
    HilR2Vec3f p_nearest;

    CHECK(hil_r2_quat_rotate_vec3(
        &out.q_nav_body,
        &p_body,
        &p_interp));

    const HilR2Quatf q0 = yaw_quat(0.0f);

    CHECK(hil_r2_quat_rotate_vec3(
        &q0,
        &p_body,
        &p_nearest));

    CHECK(nearf_abs(
        vec_distance(p_interp, p_nearest),
        0.785396f,
        2.0e-4f));

    return true;
}

static bool test_r2_002_timing_error_table(void)
{
    const float omega =
        180.0f * DEG_TO_RAD;

    struct {
        float ms;
        float expected_m;
    } cases[] = {
        {0.10f, 0.0942478f},
        {0.25f, 0.2356194f},
        {0.50f, 0.4712389f},
        {1.00f, 0.9424778f},
        {2.00f, 1.8849556f}
    };

    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        const float actual =
            hil_r2_timing_position_error_m(
                300.0f,
                omega,
                cases[i].ms * 1.0e-3f);

        CHECK(nearf_abs(
            actual,
            cases[i].expected_m,
            2.0e-5f));
    }

    return true;
}

static bool test_r2_003_holdover_2ppm(void)
{
    struct {
        float seconds;
        float expected_us;
    } cases[] = {
        {1.0f, 2.0f},
        {10.0f, 20.0f},
        {30.0f, 60.0f},
        {60.0f, 120.0f},
        {300.0f, 600.0f}
    };

    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        CHECK(nearf_abs(
            hil_r2_clock_holdover_error_us(
                2.0f,
                cases[i].seconds),
            cases[i].expected_us,
            1.0e-5f));
    }

    return true;
}

static bool test_r2_004_lever_arm_compensation(void)
{
    const HilR2Vec3f omega = {
        0.0f,
        0.0f,
        PI_F / 2.0f
    };

    const HilR2Vec3f lever = {
        0.2f,
        0.0f,
        0.0f
    };

    const HilR2Vec3f sensor_velocity =
        hil_r2_lever_arm_velocity(
            omega,
            lever);

    CHECK(nearf_abs(sensor_velocity.x, 0.0f, 1.0e-6f));
    CHECK(nearf_abs(sensor_velocity.y, 0.31415927f, 1.0e-6f));
    CHECK(nearf_abs(sensor_velocity.z, 0.0f, 1.0e-6f));

    const HilR2Vec3f los_y = {
        0.0f,
        1.0f,
        0.0f
    };

    const float raw_range_rate =
        -sensor_velocity.y;

    const float compensated =
        hil_r2_compensate_range_rate(
            raw_range_rate,
            sensor_velocity,
            los_y);

    CHECK(nearf_abs(compensated, 0.0f, 1.0e-6f));

    return true;
}

static bool test_r2_005_extrinsic_yaw_one_degree(void)
{
    const HilR2Quatf q =
        yaw_quat(1.0f * DEG_TO_RAD);

    const HilR2Vec3f input = {
        100.0f,
        0.0f,
        0.0f
    };

    HilR2Vec3f out;

    CHECK(hil_r2_quat_rotate_vec3(
        &q,
        &input,
        &out));

    CHECK(nearf_abs(out.x, 99.98477f, 2.0e-4f));
    CHECK(nearf_abs(out.y, 1.745241f, 2.0e-4f));
    CHECK(nearf_abs(out.z, 0.0f, 1.0e-6f));

    return true;
}

static bool test_r2_006_delayed_frame_rotation_error(void)
{
    const HilR2Quatf correct_q =
        yaw_quat(45.0f * DEG_TO_RAD);

    const HilR2Quatf receive_time_q =
        yaw_quat(46.8f * DEG_TO_RAD);

    const HilR2Vec3f body_los = {
        100.0f,
        0.0f,
        0.0f
    };

    HilR2Vec3f correct;
    HilR2Vec3f wrong;

    CHECK(hil_r2_quat_rotate_vec3(
        &correct_q,
        &body_los,
        &correct));

    CHECK(hil_r2_quat_rotate_vec3(
        &receive_time_q,
        &body_los,
        &wrong));

    CHECK(nearf_abs(
        vec_distance(correct, wrong),
        3.14146f,
        3.0e-4f));

    return true;
}

static bool test_r2_007_interpolation_bounds(void)
{
    HilR2HostSample a;
    HilR2HostSample b;
    HilR2HostSample out;

    memset(&a, 0, sizeof(a));
    memset(&b, 0, sizeof(b));

    a.timestamp_us = 100u;
    b.timestamp_us = 200u;

    a.q_nav_body.w = 1.0f;
    b.q_nav_body.w = 1.0f;

    CHECK(!hil_r2_host_state_interpolate(
        &a,
        &b,
        99u,
        &out));

    CHECK(!hil_r2_host_state_interpolate(
        &a,
        &b,
        201u,
        &out));

    b.timestamp_us = 100u;

    CHECK(!hil_r2_host_state_interpolate(
        &a,
        &b,
        100u,
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
        {"R2-001 yaw interpolation", test_r2_001_yaw_interpolation_5ms},
        {"R2-002 timing error table", test_r2_002_timing_error_table},
        {"R2-003 holdover", test_r2_003_holdover_2ppm},
        {"R2-004 lever arm", test_r2_004_lever_arm_compensation},
        {"R2-005 extrinsic yaw", test_r2_005_extrinsic_yaw_one_degree},
        {"R2-006 delayed frame", test_r2_006_delayed_frame_rotation_error},
        {"R2-007 interpolation bounds", test_r2_007_interpolation_bounds}
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
        "HIL-R2 DETERMINISTIC SUITE PASS (%zu tests)\n",
        count);

    return 0;
}
