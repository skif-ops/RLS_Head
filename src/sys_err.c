#include "rls/sys_err.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

static bool finite_vec3(HilR2Vec3f v)
{
    return isfinite(v.x) &&
           isfinite(v.y) &&
           isfinite(v.z);
}

static bool finite_mat3(const SysErrMat3f *m)
{
    if (m == NULL) {
        return false;
    }

    for (unsigned i = 0; i < 9u; ++i) {
        if (!isfinite(m->m[i])) {
            return false;
        }
    }

    return true;
}

static SysErrMat3f skew(HilR2Vec3f v)
{
    const SysErrMat3f out = {
        {
             0.0f, -v.z,  v.y,
             v.z,   0.0f, -v.x,
            -v.y,   v.x,  0.0f
        }
    };

    return out;
}

static SysErrMat3f matmul(
    const SysErrMat3f *a,
    const SysErrMat3f *b)
{
    SysErrMat3f out;
    memset(&out, 0, sizeof(out));

    for (unsigned r = 0; r < 3u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            float sum = 0.0f;

            for (unsigned k = 0; k < 3u; ++k) {
                sum +=
                    a->m[r * 3u + k] *
                    b->m[k * 3u + c];
            }

            out.m[r * 3u + c] = sum;
        }
    }

    return out;
}

static SysErrMat3f transpose(
    const SysErrMat3f *a)
{
    SysErrMat3f out;

    for (unsigned r = 0; r < 3u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            out.m[r * 3u + c] =
                a->m[c * 3u + r];
        }
    }

    return out;
}

bool sys_err_small_angle_position_covariance(
    HilR2Vec3f position_m,
    const SysErrMat3f *angle_cov_rad2,
    SysErrMat3f *out_position_cov_m2)
{
    if (!finite_vec3(position_m) ||
        !finite_mat3(angle_cov_rad2) ||
        out_position_cov_m2 == NULL) {
        return false;
    }

    SysErrMat3f jacobian = skew(position_m);

    /*
     * Sign of J_rot is irrelevant for J*P*J^T,
     * so [p]_x is used directly.
     */
    const SysErrMat3f tmp =
        matmul(&jacobian, angle_cov_rad2);

    const SysErrMat3f jt =
        transpose(&jacobian);

    *out_position_cov_m2 =
        matmul(&tmp, &jt);

    return finite_mat3(out_position_cov_m2);
}

bool sys_err_timing_position_covariance(
    HilR2Vec3f position_m,
    HilR2Vec3f relative_velocity_m_s,
    HilR2Vec3f angular_rate_rad_s,
    float sigma_t_s,
    SysErrMat3f *out_position_cov_m2)
{
    if (!finite_vec3(position_m) ||
        !finite_vec3(relative_velocity_m_s) ||
        !finite_vec3(angular_rate_rad_s) ||
        !isfinite(sigma_t_s) ||
        sigma_t_s < 0.0f ||
        out_position_cov_m2 == NULL) {
        return false;
    }

    const HilR2Vec3f p_cross_omega =
        hil_r2_cross(
            position_m,
            angular_rate_rad_s);

    const HilR2Vec3f j = {
        relative_velocity_m_s.x - p_cross_omega.x,
        relative_velocity_m_s.y - p_cross_omega.y,
        relative_velocity_m_s.z - p_cross_omega.z
    };

    const float variance_t =
        sigma_t_s * sigma_t_s;

    out_position_cov_m2->m[0] =
        j.x * j.x * variance_t;

    out_position_cov_m2->m[1] =
        j.x * j.y * variance_t;

    out_position_cov_m2->m[2] =
        j.x * j.z * variance_t;

    out_position_cov_m2->m[3] =
        j.y * j.x * variance_t;

    out_position_cov_m2->m[4] =
        j.y * j.y * variance_t;

    out_position_cov_m2->m[5] =
        j.y * j.z * variance_t;

    out_position_cov_m2->m[6] =
        j.z * j.x * variance_t;

    out_position_cov_m2->m[7] =
        j.z * j.y * variance_t;

    out_position_cov_m2->m[8] =
        j.z * j.z * variance_t;

    return finite_mat3(out_position_cov_m2);
}

bool sys_err_covariance_add(
    const SysErrMat3f *a,
    const SysErrMat3f *b,
    SysErrMat3f *out)
{
    if (!finite_mat3(a) ||
        !finite_mat3(b) ||
        out == NULL) {
        return false;
    }

    for (unsigned i = 0; i < 9u; ++i) {
        out->m[i] =
            a->m[i] + b->m[i];
    }

    return finite_mat3(out);
}

float sys_err_covariance_trace(
    const SysErrMat3f *cov)
{
    if (!finite_mat3(cov)) {
        return NAN;
    }

    return
        cov->m[0] +
        cov->m[4] +
        cov->m[8];
}

float sys_err_position_rms(
    const SysErrMat3f *position_cov_m2)
{
    const float trace =
        sys_err_covariance_trace(
            position_cov_m2);

    if (!isfinite(trace) || trace < 0.0f) {
        return NAN;
    }

    return sqrtf(trace);
}
