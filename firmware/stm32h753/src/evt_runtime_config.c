#include "evt_runtime_config.h"

#include "rls/hil_r1.h"

#include <math.h>
#include <string.h>

enum {
    CONFIG_WIRE_SIZE = 40,
    RECORD_PREFIX_SIZE = 8,
};

static void write_u32_le(uint8_t **p, uint32_t value)
{
    *(*p)++ = (uint8_t)value;
    *(*p)++ = (uint8_t)(value >> 8);
    *(*p)++ = (uint8_t)(value >> 16);
    *(*p)++ = (uint8_t)(value >> 24);
}

static void write_float_le(uint8_t **p, float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof(bits));
    write_u32_le(p, bits);
}

static void serialize_config(
    const evt_runtime_config_t *config,
    uint8_t wire[CONFIG_WIRE_SIZE])
{
    uint8_t *p = wire;
    write_u32_le(&p, config->schema_version);
    write_u32_le(&p, config->radar_timeout_us);
    write_u32_le(&p, config->gnss_timeout_us);
    write_u32_le(&p, config->imu_timeout_us);
    write_u32_le(&p, config->imu_freshness_us);
    write_float_le(&p, config->time_phase_sigma_us);
    write_float_le(&p, config->time_drift_sigma_ppm);
    write_float_le(&p, config->time_max_abs_rate_ppm);
    write_float_le(&p, config->host_attitude_sigma_rad);
    write_float_le(&p, config->extrinsic_sigma_rad);
}

static uint32_t record_crc32c(const evt_config_record_t *record)
{
    uint8_t wire[RECORD_PREFIX_SIZE + CONFIG_WIRE_SIZE];
    uint8_t *p = wire;
    write_u32_le(&p, record->magic);
    write_u32_le(&p, record->generation);
    serialize_config(&record->config, p);
    return crc32c_compute(wire, sizeof(wire));
}

static bool record_valid(const evt_config_record_t *record)
{
    return record != NULL
        && record->magic == EVT_CONFIG_STORE_MAGIC
        && record->generation != 0u
        && evt_runtime_config_validate(&record->config)
        && record->crc32c == record_crc32c(record);
}

void evt_runtime_config_default(evt_runtime_config_t *config)
{
    if (config == NULL) {
        return;
    }

    const evt_runtime_config_t defaults = {
        .schema_version = EVT_RUNTIME_CONFIG_SCHEMA_VERSION,
        .radar_timeout_us = 250000u,
        .gnss_timeout_us = 1500000u,
        .imu_timeout_us = 20000u,
        .imu_freshness_us = 20000u,
        .time_phase_sigma_us = 0.1f,
        .time_drift_sigma_ppm = 0.5f,
        .time_max_abs_rate_ppm = 100.0f,
        .host_attitude_sigma_rad = 0.0017453293f,
        .extrinsic_sigma_rad = 0.0034906585f,
    };
    *config = defaults;
}

bool evt_runtime_config_validate(const evt_runtime_config_t *config)
{
    return config != NULL
        && config->schema_version == EVT_RUNTIME_CONFIG_SCHEMA_VERSION
        && config->radar_timeout_us >= 10000u
        && config->radar_timeout_us <= 5000000u
        && config->gnss_timeout_us >= 500000u
        && config->gnss_timeout_us <= 10000000u
        && config->imu_timeout_us >= 1000u
        && config->imu_timeout_us <= 1000000u
        && config->imu_freshness_us >= 1000u
        && config->imu_freshness_us <= config->imu_timeout_us
        && isfinite(config->time_phase_sigma_us)
        && config->time_phase_sigma_us > 0.0f
        && config->time_phase_sigma_us <= 1000.0f
        && isfinite(config->time_drift_sigma_ppm)
        && config->time_drift_sigma_ppm > 0.0f
        && config->time_drift_sigma_ppm <= 1000.0f
        && isfinite(config->time_max_abs_rate_ppm)
        && config->time_max_abs_rate_ppm > 0.0f
        && config->time_max_abs_rate_ppm <= 10000.0f
        && isfinite(config->host_attitude_sigma_rad)
        && config->host_attitude_sigma_rad >= 0.0f
        && config->host_attitude_sigma_rad <= 0.2f
        && isfinite(config->extrinsic_sigma_rad)
        && config->extrinsic_sigma_rad >= 0.0f
        && config->extrinsic_sigma_rad <= 0.2f;
}

uint32_t evt_runtime_config_crc32c(const evt_runtime_config_t *config)
{
    if (!evt_runtime_config_validate(config)) {
        return 0u;
    }

    uint8_t wire[CONFIG_WIRE_SIZE];
    serialize_config(config, wire);
    return crc32c_compute(wire, sizeof(wire));
}

void evt_config_store_init(evt_config_store_t *store)
{
    if (store != NULL) {
        memset(store, 0, sizeof(*store));
    }
}

bool evt_config_store_load(
    const evt_config_store_t *store,
    evt_runtime_config_t *config,
    uint32_t *generation)
{
    if (store == NULL || config == NULL) {
        return false;
    }

    const bool valid0 = record_valid(&store->slots[0]);
    const bool valid1 = record_valid(&store->slots[1]);
    if (!valid0 && !valid1) {
        return false;
    }

    const evt_config_record_t *selected = &store->slots[0];
    if (!valid0 || (valid1
            && (int32_t)(store->slots[1].generation
                - store->slots[0].generation) > 0)) {
        selected = &store->slots[1];
    }

    *config = selected->config;
    if (generation != NULL) {
        *generation = selected->generation;
    }
    return true;
}

bool evt_config_store_commit(
    evt_config_store_t *store,
    const evt_runtime_config_t *config)
{
    if (store == NULL || !evt_runtime_config_validate(config)) {
        return false;
    }

    evt_runtime_config_t current;
    uint32_t generation = 0u;
    const bool have_current = evt_config_store_load(
        store, &current, &generation);
    (void)current;

    unsigned target = 0u;
    if (have_current) {
        target = record_valid(&store->slots[0])
            && store->slots[0].generation == generation ? 1u : 0u;
    }

    evt_config_record_t record;
    memset(&record, 0, sizeof(record));
    record.magic = EVT_CONFIG_STORE_MAGIC;
    record.generation = generation + 1u;
    if (record.generation == 0u) {
        record.generation = 1u;
    }
    record.config = *config;
    record.crc32c = record_crc32c(&record);
    store->slots[target] = record;
    return true;
}
