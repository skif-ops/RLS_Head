#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * HIL-R2 coordinate convention:
 * +X forward, +Y right, +Z up.
 * q_nav_body is Hamilton [w, x, y, z] and rotates Body -> Navigation.
 */

typedef struct {
    float x;
    float y;
    float z;
} HilR2Vec3f;

typedef struct {
    float w;
    float x;
    float y;
    float z;
} HilR2Quatf;

typedef struct {
    uint64_t timestamp_us;

    HilR2Vec3f position_nav_m;
    HilR2Vec3f velocity_nav_m_s;

    HilR2Quatf q_nav_body;

    HilR2Vec3f angular_rate_body_rad_s;
} HilR2HostSample;

bool hil_r2_quat_normalize(
    const HilR2Quatf *in,
    HilR2Quatf *out);

bool hil_r2_quat_slerp(
    const HilR2Quatf *a,
    const HilR2Quatf *b,
    float alpha,
    HilR2Quatf *out);

bool hil_r2_quat_rotate_vec3(
    const HilR2Quatf *q,
    const HilR2Vec3f *v,
    HilR2Vec3f *out);

bool hil_r2_host_state_interpolate(
    const HilR2HostSample *a,
    const HilR2HostSample *b,
    uint64_t target_timestamp_us,
    HilR2HostSample *out);

float hil_r2_clock_holdover_error_us(
    float drift_ppm,
    float holdover_seconds);

float hil_r2_timing_position_error_m(
    float range_m,
    float angular_rate_rad_s,
    float timing_error_seconds);

HilR2Vec3f hil_r2_cross(
    HilR2Vec3f a,
    HilR2Vec3f b);

HilR2Vec3f hil_r2_lever_arm_velocity(
    HilR2Vec3f angular_rate_rad_s,
    HilR2Vec3f lever_arm_m);

float hil_r2_compensate_range_rate(
    float raw_range_rate_m_s,
    HilR2Vec3f sensor_velocity_nav_m_s,
    HilR2Vec3f los_unit_nav);

#ifdef __cplusplus
}
#endif
