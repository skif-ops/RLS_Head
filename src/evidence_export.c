#include "rls/evidence_export.h"

#include <stddef.h>

static void put_u32_le(uint8_t *dst, uint32_t value)
{
    dst[0] = (uint8_t)(value & 0xffu);
    dst[1] = (uint8_t)((value >> 8) & 0xffu);
    dst[2] = (uint8_t)((value >> 16) & 0xffu);
    dst[3] = (uint8_t)((value >> 24) & 0xffu);
}

static void put_u64_le(uint8_t *dst, uint64_t value)
{
    for (unsigned int i = 0u; i < 8u; ++i) {
        dst[i] = (uint8_t)((value >> (8u * i)) & 0xffu);
    }
}

static uint32_t get_u32_le(const uint8_t *src)
{
    return (uint32_t)src[0]
        | ((uint32_t)src[1] << 8)
        | ((uint32_t)src[2] << 16)
        | ((uint32_t)src[3] << 24);
}

static uint64_t get_u64_le(const uint8_t *src)
{
    uint64_t value = 0u;

    for (unsigned int i = 0u; i < 8u; ++i) {
        value |= ((uint64_t)src[i]) << (8u * i);
    }

    return value;
}

static int valid_session_state(uint8_t state)
{
    return state <= (uint8_t)RLS_SESSION_CLOSED;
}

static int valid_time_state(uint8_t state)
{
    return state <= (uint8_t)TIME_SERVICE_HOLDOVER;
}

int rls_evidence_export_build(
    const rls_measurement_session_t *session,
    const TimeService *time_service,
    const rls_carrier_health_report_t *health,
    uint64_t export_local_us,
    rls_evidence_export_record_t *record
)
{
    if (
        session == NULL
        || time_service == NULL
        || health == NULL
        || record == NULL
    ) {
        return -1;
    }

    record->version = RLS_EVIDENCE_EXPORT_VERSION;
    record->session_state = (uint8_t)session->state;
    record->time_state = (uint8_t)time_service->state;
    record->healthy = health->healthy ? 1u : 0u;
    record->session_id = session->session_id;
    record->config_crc32 = session->config_crc32;
    record->health_fault_flags = health->fault_flags;
    record->radar_event_count = session->radar_event_count;
    record->imu_event_count = session->imu_event_count;
    record->gnss_event_count = session->gnss_event_count;
    record->dropped_event_count = session->dropped_event_count;
    record->started_at_us = session->started_at_us;
    record->closed_at_us = session->closed_at_us;
    record->export_local_us = export_local_us;

    return 0;
}

int rls_evidence_export_encode(
    const rls_evidence_export_record_t *record,
    uint8_t *wire,
    size_t wire_size
)
{
    if (record == NULL || wire == NULL) {
        return -1;
    }

    if (wire_size < RLS_EVIDENCE_EXPORT_WIRE_SIZE) {
        return -2;
    }

    if (
        record->version != RLS_EVIDENCE_EXPORT_VERSION
        || !valid_session_state(record->session_state)
        || !valid_time_state(record->time_state)
        || record->healthy > 1u
    ) {
        return -3;
    }

    wire[0] = record->version;
    wire[1] = record->session_state;
    wire[2] = record->time_state;
    wire[3] = record->healthy;
    put_u32_le(&wire[4], record->session_id);
    put_u32_le(&wire[8], record->config_crc32);
    put_u32_le(&wire[12], record->health_fault_flags);
    put_u32_le(&wire[16], record->radar_event_count);
    put_u32_le(&wire[20], record->imu_event_count);
    put_u32_le(&wire[24], record->gnss_event_count);
    put_u32_le(&wire[28], record->dropped_event_count);
    put_u64_le(&wire[32], record->started_at_us);
    put_u64_le(&wire[40], record->closed_at_us);
    put_u64_le(&wire[48], record->export_local_us);

    return 0;
}

int rls_evidence_export_decode(
    const uint8_t *wire,
    size_t wire_size,
    rls_evidence_export_record_t *record
)
{
    if (wire == NULL || record == NULL) {
        return -1;
    }

    if (wire_size != RLS_EVIDENCE_EXPORT_WIRE_SIZE) {
        return -2;
    }

    if (
        wire[0] != RLS_EVIDENCE_EXPORT_VERSION
        || !valid_session_state(wire[1])
        || !valid_time_state(wire[2])
        || wire[3] > 1u
    ) {
        return -3;
    }

    record->version = wire[0];
    record->session_state = wire[1];
    record->time_state = wire[2];
    record->healthy = wire[3];
    record->session_id = get_u32_le(&wire[4]);
    record->config_crc32 = get_u32_le(&wire[8]);
    record->health_fault_flags = get_u32_le(&wire[12]);
    record->radar_event_count = get_u32_le(&wire[16]);
    record->imu_event_count = get_u32_le(&wire[20]);
    record->gnss_event_count = get_u32_le(&wire[24]);
    record->dropped_event_count = get_u32_le(&wire[28]);
    record->started_at_us = get_u64_le(&wire[32]);
    record->closed_at_us = get_u64_le(&wire[40]);
    record->export_local_us = get_u64_le(&wire[48]);

    return 0;
}
