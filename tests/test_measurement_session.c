#include "rls/measurement_session.h"

#include <assert.h>

static void test_nominal_session(void)
{
    rls_measurement_session_t session;

    rls_measurement_session_init(&session);

    assert(session.state == RLS_SESSION_IDLE);

    assert(
        rls_measurement_session_arm(
            &session,
            42u,
            0x12345678u,
            1000u
        )
    );

    assert(
        rls_measurement_session_start(
            &session,
            1100u
        )
    );

    assert(
        rls_measurement_session_note_radar(
            &session
        )
    );
    assert(
        rls_measurement_session_note_imu(
            &session
        )
    );
    assert(
        rls_measurement_session_note_gnss(
            &session
        )
    );
    assert(
        rls_measurement_session_note_drop(
            &session
        )
    );

    assert(
        rls_measurement_session_close(
            &session,
            2000u
        )
    );

    assert(session.state == RLS_SESSION_CLOSED);
    assert(session.session_id == 42u);
    assert(session.config_crc32 == 0x12345678u);
    assert(session.radar_event_count == 1u);
    assert(session.imu_event_count == 1u);
    assert(session.gnss_event_count == 1u);
    assert(session.dropped_event_count == 1u);
}

static void test_invalid_transitions(void)
{
    rls_measurement_session_t session;

    rls_measurement_session_init(&session);

    assert(
        !rls_measurement_session_start(
            &session,
            1u
        )
    );

    assert(
        !rls_measurement_session_arm(
            &session,
            0u,
            0u,
            1u
        )
    );

    assert(
        rls_measurement_session_arm(
            &session,
            1u,
            0u,
            10u
        )
    );

    assert(
        !rls_measurement_session_start(
            &session,
            9u
        )
    );

    assert(
        !rls_measurement_session_note_radar(
            &session
        )
    );
}

int main(void)
{
    test_nominal_session();
    test_invalid_transitions();
    return 0;
}
