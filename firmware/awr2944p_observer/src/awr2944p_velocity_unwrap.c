#include "rls/awr2944p_velocity_unwrap.h"

#include <float.h>
#include <math.h>

static float wrapped_residual(float value, float half_period)
{
    const float period = 2.0f * half_period;
    return value - period * roundf(value / period);
}

static bool config_is_valid(
    const rls_awr2944p_velocity_unwrap_config_t *config)
{
    if (config == NULL
        || !isfinite(config->maximum_abs_velocity_m_s)
        || !isfinite(config->maximum_residual_m_s)
        || config->maximum_abs_velocity_m_s <= 0.0f
        || config->maximum_residual_m_s <= 0.0f) {
        return false;
    }
    for (size_t i = 0u; i < RLS_AWR2944P_VELOCITY_PROFILE_COUNT; ++i) {
        if (!isfinite(config->unambiguous_velocity_m_s[i])
            || config->unambiguous_velocity_m_s[i] <= 0.0f) {
            return false;
        }
    }
    return true;
}

void rls_awr2944p_velocity_unwrap_default_config(
    rls_awr2944p_velocity_unwrap_config_t *config)
{
    if (config == NULL) {
        return;
    }
    config->unambiguous_velocity_m_s[0] = 7.9562755f;
    config->unambiguous_velocity_m_s[1] = 7.2329774f;
    config->unambiguous_velocity_m_s[2] = 6.1202121f;
    config->maximum_abs_velocity_m_s = 60.0f;
    config->maximum_residual_m_s = 1.5f;
}

int rls_awr2944p_velocity_unwrap(
    const rls_awr2944p_velocity_unwrap_config_t *config,
    const float measured_velocity_m_s[RLS_AWR2944P_VELOCITY_PROFILE_COUNT],
    bool prior_valid,
    float prior_velocity_m_s,
    float *unwrapped_velocity_m_s,
    float *maximum_residual_m_s)
{
    if (!config_is_valid(config)
        || measured_velocity_m_s == NULL
        || unwrapped_velocity_m_s == NULL
        || maximum_residual_m_s == NULL
        || (prior_valid && !isfinite(prior_velocity_m_s))) {
        return -1;
    }
    for (size_t i = 0u; i < RLS_AWR2944P_VELOCITY_PROFILE_COUNT; ++i) {
        if (!isfinite(measured_velocity_m_s[i])) {
            return -1;
        }
    }

    const float half_period = config->unambiguous_velocity_m_s[0];
    const float period = 2.0f * half_period;
    const int minimum_alias = (int)ceilf(
        (-config->maximum_abs_velocity_m_s - measured_velocity_m_s[0])
        / period);
    const int maximum_alias = (int)floorf(
        (config->maximum_abs_velocity_m_s - measured_velocity_m_s[0])
        / period);

    float best_score = FLT_MAX;
    float best_prior_distance = FLT_MAX;
    float best_velocity = 0.0f;
    float best_residual = FLT_MAX;
    for (int alias = minimum_alias; alias <= maximum_alias; ++alias) {
        const float candidate = measured_velocity_m_s[0]
            + (float)alias * period;
        float score = 0.0f;
        float maximum_residual = 0.0f;
        for (size_t i = 0u; i < RLS_AWR2944P_VELOCITY_PROFILE_COUNT; ++i) {
            const float residual = fabsf(wrapped_residual(
                candidate - measured_velocity_m_s[i],
                config->unambiguous_velocity_m_s[i]));
            score += residual * residual;
            if (residual > maximum_residual) {
                maximum_residual = residual;
            }
        }
        const float prior_distance = prior_valid
            ? fabsf(candidate - prior_velocity_m_s)
            : fabsf(candidate);
        if (score < best_score - 1.0e-6f
            || (fabsf(score - best_score) <= 1.0e-6f
                && prior_distance < best_prior_distance)) {
            best_score = score;
            best_prior_distance = prior_distance;
            best_velocity = candidate;
            best_residual = maximum_residual;
        }
    }

    if (best_residual > config->maximum_residual_m_s) {
        return 1;
    }
    *unwrapped_velocity_m_s = best_velocity;
    *maximum_residual_m_s = best_residual;
    return 0;
}
