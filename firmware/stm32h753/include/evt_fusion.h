#ifndef EVT_FUSION_H
#define EVT_FUSION_H

#include "evt_runtime_config.h"
#include "icm42688p.h"
#include "rls/hil_r1.h"
#include "rls/time_service.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    EVT_FUSION_IMU_FRESH = 1u << 0,
    EVT_FUSION_TIME_LOCKED = 1u << 1,
    EVT_FUSION_TIME_HOLDOVER = 1u << 2,
    EVT_FUSION_GNSS_QUARANTINED = 1u << 3,
    EVT_FUSION_CONFIG_VALID = 1u << 4,
    EVT_FUSION_SYSERR_APPLIED = 1u << 5,
    EVT_FUSION_RADAR_STALE = 1u << 6,
    EVT_FUSION_IMU_STALE = 1u << 7,
    EVT_FUSION_POWER_FAULT = 1u << 8,
    EVT_FUSION_GNSS_DEGRADED = 1u << 9,
};

typedef struct {
    evt_runtime_config_t config;
    float angular_rate_rad_s[3];
    uint64_t last_imu_sample_us;
    uint64_t now_us;
    float time_uncertainty_us;
    uint32_t health_flags;
    uint32_t gnss_flags;
    TimeServiceState time_state;
    bool config_valid;
    bool imu_sample_valid;
} evt_fusion_context_t;

bool evt_fusion_init(
    evt_fusion_context_t *context,
    const evt_runtime_config_t *config);

void evt_fusion_note_imu(
    evt_fusion_context_t *context,
    const icm42688p_sample_t *sample,
    uint64_t timestamp_us);

void evt_fusion_update_status(
    evt_fusion_context_t *context,
    uint64_t now_us,
    TimeServiceState time_state,
    float time_uncertainty_us,
    uint32_t health_flags,
    uint32_t gnss_flags);

bool evt_fusion_apply(TargetStateV1 *state, void *context);

#ifdef __cplusplus
}
#endif

#endif
