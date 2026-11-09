#ifndef RLS_AWR2944P_VELOCITY_UNWRAP_H
#define RLS_AWR2944P_VELOCITY_UNWRAP_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RLS_AWR2944P_VELOCITY_PROFILE_COUNT 3u

typedef struct {
    float unambiguous_velocity_m_s[RLS_AWR2944P_VELOCITY_PROFILE_COUNT];
    float maximum_abs_velocity_m_s;
    float maximum_residual_m_s;
} rls_awr2944p_velocity_unwrap_config_t;

void rls_awr2944p_velocity_unwrap_default_config(
    rls_awr2944p_velocity_unwrap_config_t *config
);

int rls_awr2944p_velocity_unwrap(
    const rls_awr2944p_velocity_unwrap_config_t *config,
    const float measured_velocity_m_s[RLS_AWR2944P_VELOCITY_PROFILE_COUNT],
    bool prior_valid,
    float prior_velocity_m_s,
    float *unwrapped_velocity_m_s,
    float *maximum_residual_m_s
);

#ifdef __cplusplus
}
#endif

#endif
