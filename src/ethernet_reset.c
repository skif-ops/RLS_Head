#include "rls/ethernet_reset.h"

#include <stddef.h>
#include <string.h>

void rls_ethernet_reset_init(
    rls_ethernet_reset_t *state
)
{
    if (state == NULL) {
        return;
    }

    memset(state, 0, sizeof(*state));
}

bool rls_ethernet_reset_note_power_ready(
    rls_ethernet_reset_t *state,
    uint64_t now_us
)
{
    if (
        state == NULL
        || state->power_ready_seen
        || state->released
    ) {
        return false;
    }

    state->power_ready_us = now_us;
    state->power_ready_seen = true;
    return true;
}

rls_ethernet_reset_level_t rls_ethernet_reset_update(
    rls_ethernet_reset_t *state,
    uint64_t now_us
)
{
    if (
        state == NULL
        || !state->power_ready_seen
        || state->released
    ) {
        return (
            state != NULL && state->released
        )
            ? RLS_ETH_RESET_DRIVE_HIGH
            : RLS_ETH_RESET_ASSERT_LOW;
    }

    if (now_us < state->power_ready_us) {
        return RLS_ETH_RESET_ASSERT_LOW;
    }

    const uint64_t elapsed =
        now_us - state->power_ready_us;

    if (elapsed >= RLS_ETHERNET_RESET_MIN_DELAY_US) {
        state->released = true;
        return RLS_ETH_RESET_DRIVE_HIGH;
    }

    return RLS_ETH_RESET_ASSERT_LOW;
}

bool rls_ethernet_reset_is_released(
    const rls_ethernet_reset_t *state
)
{
    return state != NULL && state->released;
}
