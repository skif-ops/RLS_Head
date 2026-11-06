#ifndef EVT_RUNTIME_CONFIG_H
#define EVT_RUNTIME_CONFIG_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define EVT_RUNTIME_CONFIG_SCHEMA_VERSION 1u
#define EVT_CONFIG_STORE_MAGIC 0x31474643u

typedef struct {
    uint32_t schema_version;
    uint32_t radar_timeout_us;
    uint32_t gnss_timeout_us;
    uint32_t imu_timeout_us;
    uint32_t imu_freshness_us;
    float time_phase_sigma_us;
    float time_drift_sigma_ppm;
    float time_max_abs_rate_ppm;
    float host_attitude_sigma_rad;
    float extrinsic_sigma_rad;
} evt_runtime_config_t;

typedef struct {
    uint32_t magic;
    uint32_t generation;
    evt_runtime_config_t config;
    uint32_t crc32c;
} evt_config_record_t;

typedef struct {
    evt_config_record_t slots[2];
} evt_config_store_t;

void evt_runtime_config_default(evt_runtime_config_t *config);

bool evt_runtime_config_validate(const evt_runtime_config_t *config);

uint32_t evt_runtime_config_crc32c(const evt_runtime_config_t *config);

void evt_config_store_init(evt_config_store_t *store);

bool evt_config_store_commit(
    evt_config_store_t *store,
    const evt_runtime_config_t *config);

bool evt_config_store_load(
    const evt_config_store_t *store,
    evt_runtime_config_t *config,
    uint32_t *generation);

#ifdef __cplusplus
}
#endif

#endif
