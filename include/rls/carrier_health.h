#ifndef RLS_CARRIER_HEALTH_H
#define RLS_CARRIER_HEALTH_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    RLS_CARRIER_HEALTH_RADAR_STALE = 1u << 0,
    RLS_CARRIER_HEALTH_GNSS_PPS_STALE = 1u << 1,
    RLS_CARRIER_HEALTH_IMU_STALE = 1u << 2,
    RLS_CARRIER_HEALTH_POWER_FAULT = 1u << 3,
};

typedef struct {
    uint64_t radar_timeout_us;
    uint64_t gnss_pps_timeout_us;
    uint64_t imu_timeout_us;
} rls_carrier_health_limits_t;

typedef struct {
    uint64_t last_radar_ref_us;
    uint64_t last_gnss_pps_us;
    uint64_t last_imu_drdy_us;
    uint32_t power_fault_flags;
    bool radar_seen;
    bool gnss_pps_seen;
    bool imu_seen;
} rls_carrier_health_state_t;

typedef struct {
    uint32_t fault_flags;
    bool healthy;
    uint64_t radar_age_us;
    uint64_t gnss_pps_age_us;
    uint64_t imu_age_us;
} rls_carrier_health_report_t;

void rls_carrier_health_init(
    rls_carrier_health_state_t *state
);

void rls_carrier_health_note_radar_ref(
    rls_carrier_health_state_t *state,
    uint64_t timestamp_us
);

void rls_carrier_health_note_gnss_pps(
    rls_carrier_health_state_t *state,
    uint64_t timestamp_us
);

void rls_carrier_health_note_imu_drdy(
    rls_carrier_health_state_t *state,
    uint64_t timestamp_us
);

void rls_carrier_health_set_power_faults(
    rls_carrier_health_state_t *state,
    uint32_t fault_flags
);

int rls_carrier_health_evaluate(
    const rls_carrier_health_state_t *state,
    const rls_carrier_health_limits_t *limits,
    uint64_t now_us,
    rls_carrier_health_report_t *report
);

#ifdef __cplusplus
}
#endif

#endif
