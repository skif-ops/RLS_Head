#ifndef RLS_ETHERNET_RESET_H
#define RLS_ETHERNET_RESET_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RLS_ETHERNET_RESET_MIN_DELAY_US UINT64_C(25000)

typedef enum {
    RLS_ETH_RESET_ASSERT_LOW = 0,
    RLS_ETH_RESET_DRIVE_HIGH = 1
} rls_ethernet_reset_level_t;

typedef struct {
    uint64_t power_ready_us;
    bool power_ready_seen;
    bool released;
} rls_ethernet_reset_t;

void rls_ethernet_reset_init(
    rls_ethernet_reset_t *state
);

bool rls_ethernet_reset_note_power_ready(
    rls_ethernet_reset_t *state,
    uint64_t now_us
);

rls_ethernet_reset_level_t rls_ethernet_reset_update(
    rls_ethernet_reset_t *state,
    uint64_t now_us
);

bool rls_ethernet_reset_is_released(
    const rls_ethernet_reset_t *state
);

#ifdef __cplusplus
}
#endif

#endif
