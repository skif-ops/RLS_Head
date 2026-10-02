#include "rls/hil_r2.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

#define HIL_R2_EPS 1.0e-8f
#define HIL_R2_SLERP_LINEAR_DOT 0.9995f

static bool finite_vec3(HilR2Vec3f v)
{
    return isfinite(v.x) && isfinite(v.y) && isfinite(v.z);
}

static bool finite_quat(HilR2Quatf q)
{
    return isfinite(q.w) &&
           isfinite(q.x) &&
           isfinite(q.y) &&
           isfinite(q.z);
}

static HilR2Vec3f vec3_lerp(
    HilR2Vec3f a,
    HilR2Vec3f b,
    float alpha)
{
    HilR2Vec3f out = {
        a.x + (b.x - a.x) * alpha,
        a.y + (b.y - a.y) * alpha,
        a.z + (b.z - a.z) * alpha
    };

    return out;
}

bool hil_r2_quat_normalize(
    const HilR2Quatf *in,
    HilR2Quatf *out)
{
    if (in == NULL || out == NULL || !finite_quat(*in)) {
        return false;
    }

    const float norm_sq =
        in->w * in->w +
        in->x * in->x +
        in->y * in->y +
        in->z * in->z;

    if (!isfinite(norm_sq) || norm_sq <= HIL_R2_EPS) {
        return false;
    }

    const float inv_norm = 1.0f / sqrtf(norm_sq);

    out->w = in->w * inv_norm;
    out->x = in->x * inv_norm;
    out->y = in->y * inv_norm;
    out->z = in->z * inv_norm;

    return finite_quat(*out);
}

bool hil_r2_quat_slerp(
    const HilR2Quatf *a,
    const HilR2Quatf *b,
    float alpha,
    HilR2Quatf *out)
{
    if (a == NULL || b == NULL || out == NULL ||
        !isfinite(alpha) || alpha < 0.0f || alpha > 1.0f) {
        return false;
    }

    HilR2Quatf qa;
    HilR2Quatf qb;

    if (!hil_r2_quat_normalize(a, &qa) ||
        !hil_r2_quat_normalize(b, &qb)) {
        return false;
    }

    float dot =
        qa.w * qb.w +
        qa.x * qb.x +
        qa.y * qb.y +
        qa.z * qb.z;

    if (dot < 0.0f) {
        qb.w = -qb.w;
        qb.x = -qb.x;
        qb.y = -qb.y;
        qb.z = -qb.z;
        dot = -dot;
    }

    if (dot > 1.0f) {
        dot = 1.0f;
    }

    if (dot >= HIL_R2_SLERP_LINEAR_DOT) {
        HilR2Quatf linear = {
            qa.w + (qb.w - qa.w) * alpha,
            qa.x + (qb.x - qa.x) * alpha,
            qa.y + (qb.y - qa.y) * alpha,
            qa.z + (qb.z - qa.z) * alpha
        };

        return hil_r2_quat_normalize(&linear, out);
    }

    const float theta_0 = acosf(dot);
    const float sin_theta_0 = sinf(theta_0);

    if (!isfinite(theta_0) ||
        !isfinite(sin_theta_0) ||
        fabsf(sin_theta_0) <= HIL_R2_EPS) {
        return false;
    }

    const float theta = theta_0 * alpha;
    const float s1 = sinf(theta) / sin_theta_0;
    const float s0 = cosf(theta) - dot * s1;

    HilR2Quatf result = {
        s0 * qa.w + s1 * qb.w,
        s0 * qa.x + s1 * qb.x,
        s0 * qa.y + s1 * qb.y,
        s0 * qa.z + s1 * qb.z
    };

    return hil_r2_quat_normalize(&result, out);
}

bool hil_r2_quat_rotate_vec3(
    const HilR2Quatf *q,
    const HilR2Vec3f *v,
    HilR2Vec3f *out)
{
    if (q == NULL || v == NULL || out == NULL || !finite_vec3(*v)) {
        return false;
    }

    HilR2Quatf n;

    if (!hil_r2_quat_normalize(q, &n)) {
        return false;
    }

    const HilR2Vec3f qv = {n.x, n.y, n.z};
    const HilR2Vec3f t = {
        2.0f * (qv.y * v->z - qv.z * v->y),
        2.0f * (qv.z * v->x - qv.x * v->z),
        2.0f * (qv.x * v->y - qv.y * v->x)
    };

    out->x =
        v->x +
        n.w * t.x +
        (qv.y * t.z - qv.z * t.y);

    out->y =
        v->y +
        n.w * t.y +
        (qv.z * t.x - qv.x * t.z);

    out->z =
        v->z +
        n.w * t.z +
        (qv.x * t.y - qv.y * t.x);

    return finite_vec3(*out);
}

bool hil_r2_host_state_interpolate(
    const HilR2HostSample *a,
    const HilR2HostSample *b,
    uint64_t target_timestamp_us,
    HilR2HostSample *out)
{
    if (a == NULL || b == NULL || out == NULL) {
        return false;
    }

    if (b->timestamp_us <= a->timestamp_us) {
        return false;
    }

    if (target_timestamp_us < a->timestamp_us ||
        target_timestamp_us > b->timestamp_us) {
        return false;
    }

    if (!finite_vec3(a->position_nav_m) ||
        !finite_vec3(b->position_nav_m) ||
        !finite_vec3(a->velocity_nav_m_s) ||
        !finite_vec3(b->velocity_nav_m_s) ||
        !finite_vec3(a->angular_rate_body_rad_s) ||
        !finite_vec3(b->angular_rate_body_rad_s)) {
        return false;
    }

    const uint64_t span_us =
        b->timestamp_us - a->timestamp_us;

    const uint64_t offset_us =
        target_timestamp_us - a->timestamp_us;

    const float alpha =
        (float)offset_us / (float)span_us;

    memset(out, 0, sizeof(*out));
    out->timestamp_us = target_timestamp_us;

    out->position_nav_m =
        vec3_lerp(
            a->position_nav_m,
            b->position_nav_m,
            alpha);

    out->velocity_nav_m_s =
        vec3_lerp(
            a->velocity_nav_m_s,
            b->velocity_nav_m_s,
            alpha);

    out->angular_rate_body_rad_s =
        vec3_lerp(
            a->angular_rate_body_rad_s,
            b->angular_rate_body_rad_s,
            alpha);

    return hil_r2_quat_slerp(
        &a->q_nav_body,
        &b->q_nav_body,
        alpha,
        &out->q_nav_body);
}

float hil_r2_clock_holdover_error_us(
    float drift_ppm,
    float holdover_seconds)
{
    if (!isfinite(drift_ppm) ||
        !isfinite(holdover_seconds) ||
        holdover_seconds < 0.0f) {
        return NAN;
    }

    return fabsf(drift_ppm) * holdover_seconds;
}

float hil_r2_timing_position_error_m(
    float range_m,
    float angular_rate_rad_s,
    float timing_error_seconds)
{
    if (!isfinite(range_m) ||
        !isfinite(angular_rate_rad_s) ||
        !isfinite(timing_error_seconds) ||
        range_m < 0.0f ||
        timing_error_seconds < 0.0f) {
        return NAN;
    }

    return range_m *
           fabsf(angular_rate_rad_s) *
           timing_error_seconds;
}

HilR2Vec3f hil_r2_cross(
    HilR2Vec3f a,
    HilR2Vec3f b)
{
    const HilR2Vec3f out = {
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x
    };

    return out;
}

HilR2Vec3f hil_r2_lever_arm_velocity(
    HilR2Vec3f angular_rate_rad_s,
    HilR2Vec3f lever_arm_m)
{
    return hil_r2_cross(
        angular_rate_rad_s,
        lever_arm_m);
}

float hil_r2_compensate_range_rate(
    float raw_range_rate_m_s,
    HilR2Vec3f sensor_velocity_nav_m_s,
    HilR2Vec3f los_unit_nav)
{
    if (!isfinite(raw_range_rate_m_s) ||
        !finite_vec3(sensor_velocity_nav_m_s) ||
        !finite_vec3(los_unit_nav)) {
        return NAN;
    }

    const float sensor_radial =
        sensor_velocity_nav_m_s.x * los_unit_nav.x +
        sensor_velocity_nav_m_s.y * los_unit_nav.y +
        sensor_velocity_nav_m_s.z * los_unit_nav.z;

    return raw_range_rate_m_s + sensor_radial;
}
