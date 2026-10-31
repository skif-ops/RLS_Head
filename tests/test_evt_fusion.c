#include "evt_fusion.h"

#include "rls/carrier_health.h"
#include "rls/gnss_service.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#define CHECK(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return 1; \
    } \
} while (0)

static TargetStateV1 make_state(void)
{
    TargetStateV1 state;
    memset(&state, 0, sizeof(state));
    state.validity_mask = TS_VALID_POSITION | TS_VALID_VELOCITY
        | TS_VALID_POS_COV | TS_VALID_TIME;
    state.relative_position_m[0] = 100.0f;
    state.relative_position_m[1] = 20.0f;
    state.relative_velocity_m_s[0] = 5.0f;
    state.position_cov_ut[0] = 0.25f;
    state.position_cov_ut[3] = 0.25f;
    state.position_cov_ut[5] = 0.25f;
    state.timestamp_uncertainty_us = 0.5f;
    state.track_flags = TS_FLAG_TIME_VALID | TS_FLAG_COV_VALID;
    return state;
}

int main(void)
{
    evt_runtime_config_t config;
    evt_runtime_config_default(&config);
    evt_fusion_context_t fusion;
    CHECK(evt_fusion_init(&fusion, &config));

    icm42688p_sample_t sample;
    memset(&sample, 0, sizeof(sample));
    sample.angular_rate_rad_s[2] = 0.25f;
    evt_fusion_note_imu(&fusion, &sample, 990000u);
    evt_fusion_update_status(
        &fusion, 1000000u, TIME_SERVICE_LOCKED, 2.0f, 0u, 0u);

    TargetStateV1 state = make_state();
    const float base_y = state.position_cov_ut[3];
    CHECK(evt_fusion_apply(&state, &fusion));
    CHECK((state.fusion_status & EVT_FUSION_IMU_FRESH) != 0u);
    CHECK((state.fusion_status & EVT_FUSION_TIME_LOCKED) != 0u);
    CHECK((state.fusion_status & EVT_FUSION_SYSERR_APPLIED) != 0u);
    CHECK((state.validity_mask & TS_VALID_TIME) != 0u);
    CHECK(state.timestamp_uncertainty_us == 2.0f);
    CHECK(state.position_cov_ut[3] > base_y);

    state = make_state();
    evt_fusion_update_status(
        &fusion,
        2000000u,
        TIME_SERVICE_HOLDOVER,
        12.0f,
        RLS_CARRIER_HEALTH_IMU_STALE | RLS_CARRIER_HEALTH_POWER_FAULT,
        RLS_GNSS_SPOOFING);
    CHECK(evt_fusion_apply(&state, &fusion));
    CHECK((state.fusion_status & EVT_FUSION_TIME_HOLDOVER) != 0u);
    CHECK((state.fusion_status & EVT_FUSION_GNSS_QUARANTINED) != 0u);
    CHECK((state.fusion_status & EVT_FUSION_IMU_STALE) != 0u);
    CHECK((state.fusion_status & EVT_FUSION_POWER_FAULT) != 0u);
    CHECK((state.validity_mask & TS_VALID_TIME) != 0u);

    state = make_state();
    evt_fusion_update_status(
        &fusion, 2100000u, TIME_SERVICE_PHASE_ONLY, NAN, 0u,
        RLS_GNSS_TIME_INVALID);
    CHECK(evt_fusion_apply(&state, &fusion));
    CHECK((state.validity_mask & TS_VALID_TIME) == 0u);
    CHECK((state.track_flags & TS_FLAG_TIME_VALID) == 0u);

    puts("EVT fusion degradation tests passed");
    return 0;
}
