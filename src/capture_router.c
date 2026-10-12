#include "rls/capture_router.h"

#include <string.h>

bool rls_capture_router_valid_source(
    rls_capture_source_t source
)
{
    return source == RLS_CAPTURE_GNSS_PPS
        || source == RLS_CAPTURE_RADAR_REF
        || source == RLS_CAPTURE_IMU_DRDY;
}

void rls_capture_router_init(
    rls_capture_router_t *router
)
{
    if (router == NULL) {
        return;
    }

    memset(router, 0, sizeof(*router));
}

bool rls_capture_router_push(
    rls_capture_router_t *router,
    rls_capture_source_t source,
    uint64_t timestamp_us
)
{
    if (
        router == NULL
        || !rls_capture_router_valid_source(source)
    ) {
        return false;
    }

    if (router->count >= RLS_CAPTURE_ROUTER_CAPACITY) {
        router->dropped_events++;
        return false;
    }

    rls_capture_event_t *event =
        &router->events[router->head];

    event->timestamp_us = timestamp_us;
    event->source = (uint8_t)source;
    event->sequence =
        router->next_sequence[(unsigned int)source]++;
    event->reserved[0] = 0u;
    event->reserved[1] = 0u;
    event->reserved[2] = 0u;

    router->head =
        (uint16_t)(
            (router->head + 1u)
            % RLS_CAPTURE_ROUTER_CAPACITY
        );
    router->count++;

    return true;
}

bool rls_capture_router_pop(
    rls_capture_router_t *router,
    rls_capture_event_t *event
)
{
    if (
        router == NULL
        || event == NULL
        || router->count == 0u
    ) {
        return false;
    }

    *event =
        router->events[router->tail];

    router->tail =
        (uint16_t)(
            (router->tail + 1u)
            % RLS_CAPTURE_ROUTER_CAPACITY
        );
    router->count--;

    return true;
}

size_t rls_capture_router_count(
    const rls_capture_router_t *router
)
{
    if (router == NULL) {
        return 0u;
    }

    return (size_t)router->count;
}

uint32_t rls_capture_router_dropped(
    const rls_capture_router_t *router
)
{
    if (router == NULL) {
        return 0u;
    }

    return router->dropped_events;
}
