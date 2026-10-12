#include "rls/measurement_session.h"

#include <stddef.h>
#include <string.h>

static bool active(
    const rls_measurement_session_t *session
)
{
    return session != NULL
        && session->state == RLS_SESSION_ACTIVE;
}

void rls_measurement_session_init(
    rls_measurement_session_t *session
)
{
    if (session == NULL) {
        return;
    }

    memset(session, 0, sizeof(*session));
    session->state = RLS_SESSION_IDLE;
}

bool rls_measurement_session_arm(
    rls_measurement_session_t *session,
    uint32_t session_id,
    uint32_t config_crc32,
    uint64_t now_us
)
{
    if (
        session == NULL
        || session_id == 0u
        || session->state != RLS_SESSION_IDLE
    ) {
        return false;
    }

    session->session_id = session_id;
    session->config_crc32 = config_crc32;
    session->armed_at_us = now_us;
    session->state = RLS_SESSION_ARMED;

    return true;
}

bool rls_measurement_session_start(
    rls_measurement_session_t *session,
    uint64_t now_us
)
{
    if (
        session == NULL
        || session->state != RLS_SESSION_ARMED
        || now_us < session->armed_at_us
    ) {
        return false;
    }

    session->started_at_us = now_us;
    session->state = RLS_SESSION_ACTIVE;

    return true;
}

bool rls_measurement_session_note_radar(
    rls_measurement_session_t *session
)
{
    if (!active(session)) {
        return false;
    }

    session->radar_event_count++;
    return true;
}

bool rls_measurement_session_note_imu(
    rls_measurement_session_t *session
)
{
    if (!active(session)) {
        return false;
    }

    session->imu_event_count++;
    return true;
}

bool rls_measurement_session_note_gnss(
    rls_measurement_session_t *session
)
{
    if (!active(session)) {
        return false;
    }

    session->gnss_event_count++;
    return true;
}

bool rls_measurement_session_note_drop(
    rls_measurement_session_t *session
)
{
    if (!active(session)) {
        return false;
    }

    session->dropped_event_count++;
    return true;
}

bool rls_measurement_session_close(
    rls_measurement_session_t *session,
    uint64_t now_us
)
{
    if (
        session == NULL
        || session->state != RLS_SESSION_ACTIVE
        || now_us < session->started_at_us
    ) {
        return false;
    }

    session->closed_at_us = now_us;
    session->state = RLS_SESSION_CLOSED;

    return true;
}

const char *rls_measurement_session_state_name(
    rls_measurement_session_state_t state
)
{
    switch (state) {
    case RLS_SESSION_ARMED:
        return "ARMED";
    case RLS_SESSION_ACTIVE:
        return "ACTIVE";
    case RLS_SESSION_CLOSED:
        return "CLOSED";
    case RLS_SESSION_IDLE:
    default:
        return "IDLE";
    }
}
