#ifndef RLS_CAPTURE_ROUTER_H
#define RLS_CAPTURE_ROUTER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RLS_CAPTURE_ROUTER_CAPACITY 32u

typedef enum {
    RLS_CAPTURE_GNSS_PPS = 1,
    RLS_CAPTURE_RADAR_REF = 2,
    RLS_CAPTURE_IMU_DRDY = 3
} rls_capture_source_t;

typedef struct {
    uint64_t timestamp_us;
    uint32_t sequence;
    uint8_t source;
    uint8_t reserved[3];
} rls_capture_event_t;

typedef struct {
    rls_capture_event_t events[RLS_CAPTURE_ROUTER_CAPACITY];
    uint32_t next_sequence[4];
    uint32_t dropped_events;
    uint16_t head;
    uint16_t tail;
    uint16_t count;
} rls_capture_router_t;

void rls_capture_router_init(
    rls_capture_router_t *router
);

bool rls_capture_router_push(
    rls_capture_router_t *router,
    rls_capture_source_t source,
    uint64_t timestamp_us
);

bool rls_capture_router_pop(
    rls_capture_router_t *router,
    rls_capture_event_t *event
);

size_t rls_capture_router_count(
    const rls_capture_router_t *router
);

uint32_t rls_capture_router_dropped(
    const rls_capture_router_t *router
);

bool rls_capture_router_valid_source(
    rls_capture_source_t source
);

#ifdef __cplusplus
}
#endif

#endif
