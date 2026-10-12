#include "rls/ethernet_reset.h"

#include <stdio.h>

#define CHECK(expr) \
    do { \
        if (!(expr)) { \
            fprintf(stderr, "CHECK failed: %s at %s:%d\n", \
                    #expr, __FILE__, __LINE__); \
            return 1; \
        } \
    } while (0)

static int test_required_delay(void)
{
    rls_ethernet_reset_t state;

    rls_ethernet_reset_init(&state);

    CHECK(
        rls_ethernet_reset_update(
            &state,
            0u
        ) == RLS_ETH_RESET_ASSERT_LOW
    );

    CHECK(
        rls_ethernet_reset_note_power_ready(
            &state,
            1000u
        )
    );

    CHECK(
        rls_ethernet_reset_update(
            &state,
            25999u
        ) == RLS_ETH_RESET_ASSERT_LOW
    );

    CHECK(
        rls_ethernet_reset_update(
            &state,
            26000u
        ) == RLS_ETH_RESET_DRIVE_HIGH
    );

    CHECK(
        rls_ethernet_reset_is_released(
            &state
        )
    );

    return 0;
}

static int test_nonmonotonic_time_keeps_reset_asserted(void)
{
    rls_ethernet_reset_t state;

    rls_ethernet_reset_init(&state);
    CHECK(
        rls_ethernet_reset_note_power_ready(
            &state,
            5000u
        )
    );

    CHECK(
        rls_ethernet_reset_update(
            &state,
            4999u
        ) == RLS_ETH_RESET_ASSERT_LOW
    );
    CHECK(
        !rls_ethernet_reset_is_released(
            &state
        )
    );

    return 0;
}

static int test_power_ready_is_single_shot(void)
{
    rls_ethernet_reset_t state;

    rls_ethernet_reset_init(&state);
    CHECK(
        rls_ethernet_reset_note_power_ready(
            &state,
            1u
        )
    );
    CHECK(
        !rls_ethernet_reset_note_power_ready(
            &state,
            2u
        )
    );

    return 0;
}

int main(void)
{
    if (test_required_delay() != 0) {
        return 1;
    }
    if (test_nonmonotonic_time_keeps_reset_asserted() != 0) {
        return 1;
    }
    if (test_power_ready_is_single_shot() != 0) {
        return 1;
    }

    return 0;
}
