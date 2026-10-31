#include "evt_fusion.h"

#include "rls/carrier_health.h"
#include "rls/gnss_service.h"
#include "rls/targetstate_uncertainty.h"

#include <math.h>
#include <string.h>

static void set_diagonal_covariance(SysErrMat3f *matrix, float sigma)
{
    memset(matrix, 0, sizeof(*matrix));
    const float variance = sigma * sigma;
    matrix->m[0] = variance;
    matrix->m[4] = variance;
    matrix->m[8] = variance;
}

bool evt_fusion_init(
    evt_fusion_context_t *context,
    const evt_runtime_config_t *config)
{
    if (context == NULL || !evt_runtime_config_validate(config)) {
        return false;
    }

    memset(context, 0, sizeof(*context));
    context->config = *config;
    context->config_valid = true;
    context->time_state = TIME_SERVICE_UNINITIALIZED;
    return true;
}

void evt_fusion_note_imu(
    evt_fusion_context_t *context,
    const icm42688p_sample_t *sample,
    uint64_t timestamp_us)
{
    if (context == NULL || sample == NULL || timestamp_us == 0u) {
        return;
    }

    for (unsigned i = 0u; i < 3u; ++i) {
        if (!isfinite(sample->angular_rate_rad_s[i])) {
            context->imu_sample_valid = false;
            return;
        }
    }

    memcpy(
        context->angular_rate_rad_s,
        sample->angular_rate_rad_s,
        sizeof(context->angular_rate_rad_s));
    context->last_imu_sample_us = timestamp_us;
    context->imu_sample_valid = true;
}

void evt_fusion_update_status(
    evt_fusion_context_t *context,
    uint64_t now_us,
    TimeServiceState time_state,
    float time_uncertainty_us,
    uint32_t health_flags,
    uint32_t gnss_flags)
{
    if (context == NULL) {
        return;
    }

    context->now_us = now_us;
    context->time_state = time_state;
    context->time_uncertainty_us = time_uncertainty_us;
    context->health_flags = health_flags;
    context->gnss_flags = gnss_flags;
}

bool evt_fusion_apply(TargetStateV1 *state, void *opaque_context)
{
    evt_fusion_context_t *context = opaque_context;
    if (state == NULL || context == NULL || !context->config_valid) {
        return false;
    }

    uint32_t status = EVT_FUSION_CONFIG_VALID;
    const bool imu_fresh = context->imu_sample_valid
        && context->now_us >= context->last_imu_sample_us
        && context->now_us - context->last_imu_sample_us
            <= context->config.imu_freshness_us
        && (context->health_flags & RLS_CARRIER_HEALTH_IMU_STALE) == 0u;

    if (imu_fresh) {
        status |= EVT_FUSION_IMU_FRESH;
    }
    if ((context->health_flags & RLS_CARRIER_HEALTH_RADAR_STALE) != 0u) {
        status |= EVT_FUSION_RADAR_STALE;
    }
    if (!imu_fresh
        || (context->health_flags & RLS_CARRIER_HEALTH_IMU_STALE) != 0u) {
        status |= EVT_FUSION_IMU_STALE;
    }
    if ((context->health_flags & RLS_CARRIER_HEALTH_POWER_FAULT) != 0u) {
        status |= EVT_FUSION_POWER_FAULT;
    }

    const uint32_t quarantine_mask = RLS_GNSS_JAMMING | RLS_GNSS_SPOOFING;
    const bool gnss_quarantined = (context->gnss_flags & quarantine_mask) != 0u;
    const bool gnss_degraded = context->gnss_flags != 0u;
    if (gnss_quarantined) {
        status |= EVT_FUSION_GNSS_QUARANTINED;
    }
    if (gnss_degraded) {
        status |= EVT_FUSION_GNSS_DEGRADED;
    }

    const bool time_usable =
        (context->time_state == TIME_SERVICE_LOCKED
            || context->time_state == TIME_SERVICE_HOLDOVER)
        && isfinite(context->time_uncertainty_us)
        && context->time_uncertainty_us >= 0.0f;
    if (context->time_state == TIME_SERVICE_LOCKED) {
        status |= EVT_FUSION_TIME_LOCKED;
    } else if (context->time_state == TIME_SERVICE_HOLDOVER) {
        status |= EVT_FUSION_TIME_HOLDOVER;
    }

    if (time_usable) {
        if (context->time_uncertainty_us > state->timestamp_uncertainty_us) {
            state->timestamp_uncertainty_us = context->time_uncertainty_us;
        }
        state->validity_mask |= TS_VALID_TIME;
        state->track_flags |= TS_FLAG_TIME_VALID;
    } else {
        state->validity_mask &= ~TS_VALID_TIME;
        state->track_flags &= ~TS_FLAG_TIME_VALID;
    }

    TargetStateSysErrInputs inputs;
    memset(&inputs, 0, sizeof(inputs));
    set_diagonal_covariance(
        &inputs.host_attitude_cov_rad2,
        context->config.host_attitude_sigma_rad);
    set_diagonal_covariance(
        &inputs.extrinsic_rotation_cov_rad2,
        context->config.extrinsic_sigma_rad);
    if (imu_fresh) {
        inputs.angular_rate_rad_s.x = context->angular_rate_rad_s[0];
        inputs.angular_rate_rad_s.y = context->angular_rate_rad_s[1];
        inputs.angular_rate_rad_s.z = context->angular_rate_rad_s[2];
    }
    inputs.timestamp_sigma_s = time_usable
        ? context->time_uncertainty_us * 1.0e-6f
        : 0.0f;

    TargetStateSysErrResult result;
    if (!targetstate_apply_sys_err(state, &inputs, &result)) {
        return false;
    }
    status |= EVT_FUSION_SYSERR_APPLIED;
    state->fusion_status = status;
    return true;
}
