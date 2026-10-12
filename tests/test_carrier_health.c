#include "rls/carrier_health.h"

#include <stdint.h>

static int test_healthy(void)
{
    rls_carrier_health_state_t state;
    rls_carrier_health_report_t report;
    const rls_carrier_health_limits_t limits = {
        .radar_timeout_us = 100000u,
        .gnss_pps_timeout_us = 1500000u,
        .imu_timeout_us = 20000u,
    };

    rls_carrier_health_init(&state);
    rls_carrier_health_note_radar_ref(&state, 1000000u);
    rls_carrier_health_note_gnss_pps(&state, 1000000u);
    rls_carrier_health_note_imu_drdy(&state, 1095000u);

    if (
        rls_carrier_health_evaluate(
            &state,
            &limits,
            1100000u,
            &report
        ) != 0
    ) {
        return 1;
    }

    return (
        report.healthy
        && report.fault_flags == 0u
        && report.radar_age_us == 100000u
        && report.gnss_pps_age_us == 100000u
        && report.imu_age_us == 5000u
    ) ? 0 : 2;
}

static int test_stale_and_power_faults(void)
{
    rls_carrier_health_state_t state;
    rls_carrier_health_report_t report;
    const rls_carrier_health_limits_t limits = {
        .radar_timeout_us = 100000u,
        .gnss_pps_timeout_us = 1500000u,
        .imu_timeout_us = 20000u,
    };

    rls_carrier_health_init(&state);
    rls_carrier_health_note_radar_ref(&state, 1u);
    rls_carrier_health_note_gnss_pps(&state, 1u);
    rls_carrier_health_note_imu_drdy(&state, 1u);
    rls_carrier_health_set_power_faults(&state, 0x02u);

    if (
        rls_carrier_health_evaluate(
            &state,
            &limits,
            2000000u,
            &report
        ) != 0
    ) {
        return 1;
    }

    return (
        !report.healthy
        && (
            report.fault_flags
            & RLS_CARRIER_HEALTH_RADAR_STALE
        ) != 0u
        && (
            report.fault_flags
            & RLS_CARRIER_HEALTH_GNSS_PPS_STALE
        ) != 0u
        && (
            report.fault_flags
            & RLS_CARRIER_HEALTH_IMU_STALE
        ) != 0u
        && (
            report.fault_flags
            & RLS_CARRIER_HEALTH_POWER_FAULT
        ) != 0u
    ) ? 0 : 2;
}

static int test_never_seen_is_stale(void)
{
    rls_carrier_health_state_t state;
    rls_carrier_health_report_t report;
    const rls_carrier_health_limits_t limits = {
        .radar_timeout_us = 100u,
        .gnss_pps_timeout_us = 100u,
        .imu_timeout_us = 100u,
    };

    rls_carrier_health_init(&state);

    if (
        rls_carrier_health_evaluate(
            &state,
            &limits,
            10u,
            &report
        ) != 0
    ) {
        return 1;
    }

    return (
        report.fault_flags
        == (
            RLS_CARRIER_HEALTH_RADAR_STALE
            | RLS_CARRIER_HEALTH_GNSS_PPS_STALE
            | RLS_CARRIER_HEALTH_IMU_STALE
        )
    ) ? 0 : 2;
}

int main(void)
{
    if (test_healthy() != 0) {
        return 1;
    }

    if (test_stale_and_power_faults() != 0) {
        return 2;
    }

    if (test_never_seen_is_stale() != 0) {
        return 3;
    }

    return 0;
}
