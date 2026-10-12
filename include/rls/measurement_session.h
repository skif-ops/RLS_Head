#ifndef RLS_MEASUREMENT_SESSION_H
#define RLS_MEASUREMENT_SESSION_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    RLS_SESSION_IDLE = 0,
    RLS_SESSION_ARMED,
    RLS_SESSION_ACTIVE,
    RLS_SESSION_CLOSED
} rls_measurement_session_state_t;

typedef struct {
    uint32_t session_id;
    uint32_t config_crc32;
    uint64_t armed_at_us;
    uint64_t started_at_us;
    uint64_t closed_at_us;
    uint32_t radar_event_count;
    uint32_t imu_event_count;
    uint32_t gnss_event_count;
    uint32_t dropped_event_count;
    rls_measurement_session_state_t state;
} rls_measurement_session_t;

void rls_measurement_session_init(
    rls_measurement_session_t *session
);

bool rls_measurement_session_arm(
    rls_measurement_session_t *session,
    uint32_t session_id,
    uint32_t config_crc32,
    uint64_t now_us
);

bool rls_measurement_session_start(
    rls_measurement_session_t *session,
    uint64_t now_us
);

bool rls_measurement_session_note_radar(
    rls_measurement_session_t *session
);

bool rls_measurement_session_note_imu(
    rls_measurement_session_t *session
);

bool rls_measurement_session_note_gnss(
    rls_measurement_session_t *session
);

bool rls_measurement_session_note_drop(
    rls_measurement_session_t *session
);

bool rls_measurement_session_close(
    rls_measurement_session_t *session,
    uint64_t now_us
);

const char *rls_measurement_session_state_name(
    rls_measurement_session_state_t state
);

#ifdef __cplusplus
}
#endif

#endif
