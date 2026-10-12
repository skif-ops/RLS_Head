#include "rls/capture_router.h"

#include <assert.h>
#include <stdint.h>

static void test_fifo_and_per_source_sequence(void)
{
    rls_capture_router_t router;
    rls_capture_event_t event;

    rls_capture_router_init(&router);

    assert(
        rls_capture_router_push(
            &router,
            RLS_CAPTURE_GNSS_PPS,
            100u
        )
    );

    assert(
        rls_capture_router_push(
            &router,
            RLS_CAPTURE_RADAR_REF,
            110u
        )
    );

    assert(
        rls_capture_router_push(
            &router,
            RLS_CAPTURE_GNSS_PPS,
            200u
        )
    );

    assert(rls_capture_router_count(&router) == 3u);

    assert(rls_capture_router_pop(&router, &event));
    assert(event.source == RLS_CAPTURE_GNSS_PPS);
    assert(event.timestamp_us == 100u);
    assert(event.sequence == 0u);

    assert(rls_capture_router_pop(&router, &event));
    assert(event.source == RLS_CAPTURE_RADAR_REF);
    assert(event.timestamp_us == 110u);
    assert(event.sequence == 0u);

    assert(rls_capture_router_pop(&router, &event));
    assert(event.source == RLS_CAPTURE_GNSS_PPS);
    assert(event.timestamp_us == 200u);
    assert(event.sequence == 1u);

    assert(!rls_capture_router_pop(&router, &event));
}

static void test_overflow_is_counted(void)
{
    rls_capture_router_t router;

    rls_capture_router_init(&router);

    for (unsigned int i = 0u;
         i < RLS_CAPTURE_ROUTER_CAPACITY;
         ++i) {
        assert(
            rls_capture_router_push(
                &router,
                RLS_CAPTURE_IMU_DRDY,
                (uint64_t)i
            )
        );
    }

    assert(
        !rls_capture_router_push(
            &router,
            RLS_CAPTURE_IMU_DRDY,
            999u
        )
    );

    assert(
        rls_capture_router_dropped(&router)
        == 1u
    );
}

static void test_invalid_source_rejected(void)
{
    rls_capture_router_t router;

    rls_capture_router_init(&router);

    assert(
        !rls_capture_router_push(
            &router,
            (rls_capture_source_t)0,
            1u
        )
    );
}

int main(void)
{
    test_fifo_and_per_source_sequence();
    test_overflow_is_counted();
    test_invalid_source_rejected();
    return 0;
}
