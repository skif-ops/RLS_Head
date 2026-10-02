#include "rls/targetstate_uncertainty.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

static bool finite_ut6(const float ut[6])
{
    if (ut == NULL) {
        return false;
    }

    for (unsigned i = 0; i < 6u; ++i) {
        if (!isfinite(ut[i])) {
            return false;
        }
    }

    return
        ut[0] >= 0.0f &&
        ut[3] >= 0.0f &&
        ut[5] >= 0.0f;
}

static SysErrMat3f ut6_to_mat3(
    const float ut[6])
{
    const SysErrMat3f out = {
        {
            ut[0], ut[1], ut[2],
            ut[1], ut[3], ut[4],
            ut[2], ut[4], ut[5]
        }
    };

    return out;
}

static void mat3_to_ut6(
    const SysErrMat3f *m,
    float ut[6])
{
    ut[0] = m->m[0];

    ut[1] =
        0.5f *
        (m->m[1] + m->m[3]);

    ut[2] =
        0.5f *
        (m->m[2] + m->m[6]);

    ut[3] = m->m[4];

    ut[4] =
        0.5f *
        (m->m[5] + m->m[7]);

    ut[5] = m->m[8];
}

static bool covariance_add3(
    const SysErrMat3f *a,
    const SysErrMat3f *b,
    const SysErrMat3f *c,
    SysErrMat3f *out)
{
    SysErrMat3f ab;

    if (!sys_err_covariance_add(
            a,
            b,
            &ab)) {
        return false;
    }

    return sys_err_covariance_add(
        &ab,
        c,
        out);
}

bool targetstate_apply_sys_err(
    TargetStateV1 *state,
    const TargetStateSysErrInputs *inputs,
    TargetStateSysErrResult *result)
{
    if (state == NULL ||
        inputs == NULL ||
        result == NULL) {
        return false;
    }

    if (!finite_ut6(state->position_cov_ut)) {
        return false;
    }

    const HilR2Vec3f position = {
        state->relative_position_m[0],
        state->relative_position_m[1],
        state->relative_position_m[2]
    };

    const HilR2Vec3f relative_velocity = {
        state->relative_velocity_m_s[0],
        state->relative_velocity_m_s[1],
        state->relative_velocity_m_s[2]
    };

    TargetStateSysErrResult local;
    memset(&local, 0, sizeof(local));

    if (!sys_err_small_angle_position_covariance(
            position,
            &inputs->host_attitude_cov_rad2,
            &local.attitude_position_cov_m2)) {
        return false;
    }

    if (!sys_err_small_angle_position_covariance(
            position,
            &inputs->extrinsic_rotation_cov_rad2,
            &local.extrinsic_position_cov_m2)) {
        return false;
    }

    if (!sys_err_timing_position_covariance(
            position,
            relative_velocity,
            inputs->angular_rate_rad_s,
            inputs->timestamp_sigma_s,
            &local.timestamp_position_cov_m2)) {
        return false;
    }

    if (!covariance_add3(
            &local.attitude_position_cov_m2,
            &local.timestamp_position_cov_m2,
            &local.extrinsic_position_cov_m2,
            &local.added_position_cov_m2)) {
        return false;
    }

    local.base_position_cov_m2 =
        ut6_to_mat3(
            state->position_cov_ut);

    if (!sys_err_covariance_add(
            &local.base_position_cov_m2,
            &local.added_position_cov_m2,
            &local.total_position_cov_m2)) {
        return false;
    }

    local.added_position_rms_m =
        sys_err_position_rms(
            &local.added_position_cov_m2);

    local.total_position_rms_m =
        sys_err_position_rms(
            &local.total_position_cov_m2);

    if (!isfinite(local.added_position_rms_m) ||
        !isfinite(local.total_position_rms_m)) {
        return false;
    }

    mat3_to_ut6(
        &local.total_position_cov_m2,
        state->position_cov_ut);

    state->validity_mask |=
        TS_VALID_POS_COV;

    *result = local;

    return true;
}
