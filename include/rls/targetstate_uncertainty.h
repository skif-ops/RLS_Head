#pragma once

#include <stdbool.h>

#include "rls/hil_r1.h"
#include "rls/sys_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    SysErrMat3f host_attitude_cov_rad2;
    SysErrMat3f extrinsic_rotation_cov_rad2;

    HilR2Vec3f angular_rate_rad_s;

    float timestamp_sigma_s;
} TargetStateSysErrInputs;

typedef struct {
    SysErrMat3f base_position_cov_m2;
    SysErrMat3f attitude_position_cov_m2;
    SysErrMat3f timestamp_position_cov_m2;
    SysErrMat3f extrinsic_position_cov_m2;

    SysErrMat3f added_position_cov_m2;
    SysErrMat3f total_position_cov_m2;

    float added_position_rms_m;
    float total_position_rms_m;
} TargetStateSysErrResult;

/*
 * Augments TargetStateV1 position covariance only.
 *
 * The 200-byte wire format is unchanged.
 * timestamp_uncertainty_us is not modified here; callers retain explicit
 * ownership of the timestamp field to avoid double counting uncertainty.
 */
bool targetstate_apply_sys_err(
    TargetStateV1 *state,
    const TargetStateSysErrInputs *inputs,
    TargetStateSysErrResult *result);

#ifdef __cplusplus
}
#endif
