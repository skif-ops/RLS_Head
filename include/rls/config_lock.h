#ifndef RLS_CONFIG_LOCK_H
#define RLS_CONFIG_LOCK_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    RLS_CONFIG_EMPTY = 0,
    RLS_CONFIG_STAGED,
    RLS_CONFIG_LOCKED
} rls_config_state_t;

typedef struct {
    uint32_t version;
    uint32_t crc32;
    uint32_t length;
    rls_config_state_t state;
} rls_config_lock_t;

void rls_config_lock_init(
    rls_config_lock_t *lock
);

uint32_t rls_config_crc32(
    const uint8_t *data,
    size_t length
);

bool rls_config_lock_stage(
    rls_config_lock_t *lock,
    uint32_t version,
    const uint8_t *data,
    size_t length
);

bool rls_config_lock_commit(
    rls_config_lock_t *lock
);

bool rls_config_lock_verify(
    const rls_config_lock_t *lock,
    uint32_t version,
    const uint8_t *data,
    size_t length
);

bool rls_config_lock_reset(
    rls_config_lock_t *lock
);

const char *rls_config_lock_state_name(
    rls_config_state_t state
);

#ifdef __cplusplus
}
#endif

#endif
