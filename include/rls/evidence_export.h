#ifndef RLS_EVIDENCE_EXPORT_H
#define RLS_EVIDENCE_EXPORT_H

#include "rls/carrier_health.h"
#include "rls/measurement_session.h"
#include "rls/time_service.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RLS_EVIDENCE_EXPORT_VERSION 1u
#define RLS_EVIDENCE_EXPORT_WIRE_SIZE 56u

typedef struct {
    uint8_t version;
    uint8_t session_state;
    uint8_t time_state;
    uint8_t healthy;
    uint32_t session_id;
    uint32_t config_crc32;
    uint32_t health_fault_flags;
    uint32_t radar_event_count;
    uint32_t imu_event_count;
    uint32_t gnss_event_count;
    uint32_t dropped_event_count;
    uint64_t started_at_us;
    uint64_t closed_at_us;
    uint64_t export_local_us;
} rls_evidence_export_record_t;

int rls_evidence_export_build(
    const rls_measurement_session_t *session,
    const TimeService *time_service,
    const rls_carrier_health_report_t *health,
    uint64_t export_local_us,
    rls_evidence_export_record_t *record
);

int rls_evidence_export_encode(
    const rls_evidence_export_record_t *record,
    uint8_t *wire,
    size_t wire_size
);

int rls_evidence_export_decode(
    const uint8_t *wire,
    size_t wire_size,
    rls_evidence_export_record_t *record
);

#ifdef __cplusplus
}
#endif

#endif
