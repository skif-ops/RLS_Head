#include "rls/measurement_session.h"

#include <stdio.h>

#define CHECK(expr) \
    do { \
        if (!(expr)) { \
            fprintf(stderr, "CHECK failed: %s at %s:%d\n", \
                    #expr, __FILE__, __LINE__); \
            return 1; \
        } \
    } while (0)

static int test_nominal_session(void)
{
    rls_measurement_session_t session;

    rls_measurement_session_init(&session);

    CHECK(session.state == RLS_SESSION_IDLE);

    CHECK(rls_measurement_session_arm(
        &session,
        42u,
        0x12345678u,
        1000u));

    CHECK(rls_measurement_session_start(
        &session,
        1100u));

    CHECK(rls_measurement_session_note_radar(&session));
    CHECK(rls_measurement_session_note_imu(&session));
    CHECK(rls_measurement_session_note_gnss(&session));
    CHECK(rls_measurement_session_note_drop(&session));

    CHECK(rls_measurement_session_close(
        &session,
        2000u));

    CHECK(session.state == RLS_SESSION_CLOSED);
    CHECK(session.session_id == 42u);
    CHECK(session.config_crc32 == 0x12345678u);
    CHECK(session.radar_event_count == 1u);
    CHECK(session.imu_event_count == 1u);
    CHECK(session.gnss_event_count == 1u);
    CHECK(session.dropped_event_count == 1u);

    return 0;
}

static int test_invalid_transitions(void)
{
    rls_measurement_session_t session;

    rls_measurement_session_init(&session);

    CHECK(!rls_measurement_session_start(
        &session,
        1u));

    CHECK(!rls_measurement_session_arm(
        &session,
        0u,
        0u,
        1u));

    CHECK(rls_measurement_session_arm(
        &session,
        1u,
        0u,
        10u));

    CHECK(!rls_measurement_session_start(
        &session,
        9u));

    CHECK(!rls_measurement_session_note_radar(
        &session));

    return 0;
}

int main(void)
{
    if (test_nominal_session() != 0) {
        return 1;
    }
    if (test_invalid_transitions() != 0) {
        return 1;
    }

    return 0;
}
