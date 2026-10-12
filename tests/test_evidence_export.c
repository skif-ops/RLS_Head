#include "rls/evidence_export.h"

#include <stdio.h>
#include <string.h>

#define CHECK(expr) \
    do { \
        if (!(expr)) { \
            fprintf(stderr, "CHECK failed: %s at %s:%d\n", \
                    #expr, __FILE__, __LINE__); \
            return 1; \
        } \
    } while (0)

static int test_round_trip(void)
{
    rls_measurement_session_t session;
    rls_carrier_health_report_t health = {
        .fault_flags = 0u,
        .healthy = true,
        .radar_age_us = 10u,
        .gnss_pps_age_us = 20u,
        .imu_age_us = 5u,
    };
    TimeService time_service;
    rls_evidence_export_record_t record;
    rls_evidence_export_record_t decoded;
    uint8_t wire[RLS_EVIDENCE_EXPORT_WIRE_SIZE];

    rls_measurement_session_init(&session);
    CHECK(rls_measurement_session_arm(
        &session, 7u, 0xAABBCCDDu, 100u));
    CHECK(rls_measurement_session_start(
        &session, 110u));
    CHECK(rls_measurement_session_note_radar(&session));
    CHECK(rls_measurement_session_note_imu(&session));
    CHECK(rls_measurement_session_note_gnss(&session));
    CHECK(rls_measurement_session_close(
        &session, 200u));

    CHECK(time_service_init(
        &time_service, 0.25f, 2.0f, 100.0f));
    CHECK(time_service_observe_pps(
        &time_service, 1000u, 10000)
        == TIME_OBSERVE_ACCEPTED_PHASE);

    CHECK(rls_evidence_export_build(
        &session,
        &time_service,
        &health,
        250u,
        &record) == 0);

    CHECK(rls_evidence_export_encode(
        &record,
        wire,
        sizeof(wire)) == 0);

    memset(&decoded, 0, sizeof(decoded));

    CHECK(rls_evidence_export_decode(
        wire,
        sizeof(wire),
        &decoded) == 0);

    CHECK(decoded.session_id == 7u);
    CHECK(decoded.config_crc32 == 0xAABBCCDDu);
    CHECK(decoded.session_state == RLS_SESSION_CLOSED);
    CHECK(decoded.time_state == TIME_SERVICE_PHASE_ONLY);
    CHECK(decoded.healthy == 1u);
    CHECK(decoded.radar_event_count == 1u);
    CHECK(decoded.imu_event_count == 1u);
    CHECK(decoded.gnss_event_count == 1u);
    CHECK(decoded.dropped_event_count == 0u);
    CHECK(decoded.started_at_us == 110u);
    CHECK(decoded.closed_at_us == 200u);
    CHECK(decoded.export_local_us == 250u);

    return 0;
}

static int test_invalid_wire_rejected(void)
{
    uint8_t wire[RLS_EVIDENCE_EXPORT_WIRE_SIZE] = {0};
    rls_evidence_export_record_t decoded;

    wire[0] = 99u;

    CHECK(rls_evidence_export_decode(
        wire,
        sizeof(wire),
        &decoded) == -3);

    return 0;
}

int main(void)
{
    if (test_round_trip() != 0) {
        return 1;
    }
    if (test_invalid_wire_rejected() != 0) {
        return 1;
    }

    return 0;
}
