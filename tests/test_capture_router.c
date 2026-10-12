#include "rls/capture_router.h"

#include <stdint.h>
#include <stdio.h>

#define CHECK(expr) \
    do { \
        if (!(expr)) { \
            fprintf(stderr, "CHECK failed: %s:%d: %s\n", \
                    __FILE__, __LINE__, #expr); \
            return 1; \
        } \
    } while (0)

static int test_fifo_and_per_source_sequence(void)
{
    rls_capture_router_t router;
    rls_capture_event_t event;

    rls_capture_router_init(&router);

    CHECK(
        rls_capture_router_push(
            &router,
            RLS_CAPTURE_GNSS_PPS,
            100u
        )
    );

    CHECK(
        rls_capture_router_push(
            &router,
            RLS_CAPTURE_RADAR_REF,
            110u
        )
    );

    CHECK(
        rls_capture_router_push(
            &router,
            RLS_CAPTURE_GNSS_PPS,
            200u
        )
    );

    CHECK(rls_capture_router_count(&router) == 3u);

    CHECK(rls_capture_router_pop(&router, &event));
    CHECK(event.source == RLS_CAPTURE_GNSS_PPS);
    CHECK(event.timestamp_us == 100u);
    CHECK(event.sequence == 0u);

    CHECK(rls_capture_router_pop(&router, &event));
    CHECK(event.source == RLS_CAPTURE_RADAR_REF);
    CHECK(event.timestamp_us == 110u);
    CHECK(event.sequence == 0u);

    CHECK(rls_capture_router_pop(&router, &event));
    CHECK(event.source == RLS_CAPTURE_GNSS_PPS);
    CHECK(event.timestamp_us == 200u);
    CHECK(event.sequence == 1u);

    CHECK(!rls_capture_router_pop(&router, &event));

    return 0;
}

static int test_overflow_is_counted(void)
{
    rls_capture_router_t router;

    rls_capture_router_init(&router);

    for (unsigned int i = 0u;
         i < RLS_CAPTURE_ROUTER_CAPACITY;
         ++i) {
        CHECK(
            rls_capture_router_push(
                &router,
                RLS_CAPTURE_IMU_DRDY,
                (uint64_t)i
            )
        );
    }

    CHECK(
        !rls_capture_router_push(
            &router,
            RLS_CAPTURE_IMU_DRDY,
            999u
        )
    );

    CHECK(
        rls_capture_router_dropped(&router)
        == 1u
    );

    return 0;
}

static int test_invalid_source_rejected(void)
{
    rls_capture_router_t router;

    rls_capture_router_init(&router);

    CHECK(
        !rls_capture_router_push(
            &router,
            (rls_capture_source_t)0,
            1u
        )
    );

    return 0;
}

int main(void)
{
    if (test_fifo_and_per_source_sequence() != 0) {
        return 1;
    }

    if (test_overflow_is_counted() != 0) {
        return 1;
    }

    if (test_invalid_source_rejected() != 0) {
        return 1;
    }

    return 0;
}
