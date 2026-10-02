#pragma once

#include <stdbool.h>

#include "rls/hil_r2.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float m[9];
} SysErrMat3f;

/*
 * First-order small-angle covariance:
 * J_rot = -[p]_x
 * P_pos = J_rot * P_angle * J_rot^T
 */
bool sys_err_small_angle_position_covariance(
    HilR2Vec3f position_m,
    const SysErrMat3f *angle_cov_rad2,
    SysErrMat3f *out_position_cov_m2);

/*
 * First-order timestamp covariance:
 * J_t = v_rel - [p]_x * omega
 * P_time = J_t * sigma_t^2 * J_t^T
 */
bool sys_err_timing_position_covariance(
    HilR2Vec3f position_m,
    HilR2Vec3f relative_velocity_m_s,
    HilR2Vec3f angular_rate_rad_s,
    float sigma_t_s,
    SysErrMat3f *out_position_cov_m2);

bool sys_err_covariance_add(
    const SysErrMat3f *a,
    const SysErrMat3f *b,
    SysErrMat3f *out);

float sys_err_covariance_trace(
    const SysErrMat3f *cov);

float sys_err_position_rms(
    const SysErrMat3f *position_cov_m2);

#ifdef __cplusplus
}
#endif
