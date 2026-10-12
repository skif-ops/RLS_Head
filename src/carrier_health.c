#include "rls/carrier_health.h"

#include <stddef.h>
#include <string.h>

static uint64_t age_us(
    uint64_t now_us,
    uint64_t timestamp_us
)
{
    if (now_us < timestamp_us) {
        return UINT64_MAX;
    }

    return now_us - timestamp_us;
}

void rls_carrier_health_init(
    rls_carrier_health_state_t *state
)
{
    if (state == NULL) {
        return;
    }

    memset(state, 0, sizeof(*state));
}

void rls_carrier_health_note_radar_ref(
    rls_carrier_health_state_t *state,
    uint64_t timestamp_us
)
{
    if (state == NULL) {
        return;
    }

    state->last_radar_ref_us = timestamp_us;
    state->radar_seen = true;
}

void rls_carrier_health_note_gnss_pps(
    rls_carrier_health_state_t *state,
    uint64_t timestamp_us
)
{
    if (state == NULL) {
        return;
    }

    state->last_gnss_pps_us = timestamp_us;
    state->gnss_pps_seen = true;
}

void rls_carrier_health_note_imu_drdy(
    rls_carrier_health_state_t *state,
    uint64_t timestamp_us
)
{
    if (state == NULL) {
        return;
    }

    state->last_imu_drdy_us = timestamp_us;
    state->imu_seen = true;
}

void rls_carrier_health_set_power_faults(
    rls_carrier_health_state_t *state,
    uint32_t fault_flags
)
{
    if (state == NULL) {
        return;
    }

    state->power_fault_flags = fault_flags;
}

int rls_carrier_health_evaluate(
    const rls_carrier_health_state_t *state,
    const rls_carrier_health_limits_t *limits,
    uint64_t now_us,
    rls_carrier_health_report_t *report
)
{
    uint32_t faults = 0u;

    if (
        state == NULL
        || limits == NULL
        || report == NULL
    ) {
        return -1;
    }

    report->radar_age_us = state->radar_seen
        ? age_us(now_us, state->last_radar_ref_us)
        : UINT64_MAX;
    report->gnss_pps_age_us = state->gnss_pps_seen
        ? age_us(now_us, state->last_gnss_pps_us)
        : UINT64_MAX;
    report->imu_age_us = state->imu_seen
        ? age_us(now_us, state->last_imu_drdy_us)
        : UINT64_MAX;

    if (
        !state->radar_seen
        || report->radar_age_us > limits->radar_timeout_us
    ) {
        faults |= RLS_CARRIER_HEALTH_RADAR_STALE;
    }

    if (
        !state->gnss_pps_seen
        || report->gnss_pps_age_us > limits->gnss_pps_timeout_us
    ) {
        faults |= RLS_CARRIER_HEALTH_GNSS_PPS_STALE;
    }

    if (
        !state->imu_seen
        || report->imu_age_us > limits->imu_timeout_us
    ) {
        faults |= RLS_CARRIER_HEALTH_IMU_STALE;
    }

    if (state->power_fault_flags != 0u) {
        faults |= RLS_CARRIER_HEALTH_POWER_FAULT;
    }

    report->fault_flags = faults;
    report->healthy = (faults == 0u);

    return 0;
}
