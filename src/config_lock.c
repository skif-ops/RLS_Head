#include "rls/config_lock.h"

#include <limits.h>
#include <stddef.h>
#include <string.h>

#define CRC32_POLY UINT32_C(0xEDB88320)

void rls_config_lock_init(
    rls_config_lock_t *lock
)
{
    if (lock == NULL) {
        return;
    }

    memset(lock, 0, sizeof(*lock));
    lock->state = RLS_CONFIG_EMPTY;
}

uint32_t rls_config_crc32(
    const uint8_t *data,
    size_t length
)
{
    if (data == NULL && length != 0u) {
        return 0u;
    }

    uint32_t crc = UINT32_C(0xFFFFFFFF);

    for (size_t i = 0u; i < length; ++i) {
        crc ^= (uint32_t)data[i];

        for (unsigned int bit = 0u; bit < 8u; ++bit) {
            const uint32_t mask =
                (uint32_t)-(int32_t)(crc & 1u);
            crc =
                (crc >> 1)
                ^ (CRC32_POLY & mask);
        }
    }

    return ~crc;
}

bool rls_config_lock_stage(
    rls_config_lock_t *lock,
    uint32_t version,
    const uint8_t *data,
    size_t length
)
{
    if (
        lock == NULL
        || version == 0u
        || (data == NULL && length != 0u)
        || length > UINT32_MAX
        || lock->state == RLS_CONFIG_LOCKED
    ) {
        return false;
    }

    lock->version = version;
    lock->length = (uint32_t)length;
    lock->crc32 =
        rls_config_crc32(
            data,
            length
        );
    lock->state = RLS_CONFIG_STAGED;

    return true;
}

bool rls_config_lock_commit(
    rls_config_lock_t *lock
)
{
    if (
        lock == NULL
        || lock->state != RLS_CONFIG_STAGED
    ) {
        return false;
    }

    lock->state = RLS_CONFIG_LOCKED;
    return true;
}

bool rls_config_lock_verify(
    const rls_config_lock_t *lock,
    uint32_t version,
    const uint8_t *data,
    size_t length
)
{
    if (
        lock == NULL
        || lock->state != RLS_CONFIG_LOCKED
        || version != lock->version
        || length != (size_t)lock->length
        || (data == NULL && length != 0u)
    ) {
        return false;
    }

    return rls_config_crc32(
        data,
        length
    ) == lock->crc32;
}

bool rls_config_lock_reset(
    rls_config_lock_t *lock
)
{
    if (lock == NULL) {
        return false;
    }

    rls_config_lock_init(lock);
    return true;
}

const char *rls_config_lock_state_name(
    rls_config_state_t state
)
{
    switch (state) {
    case RLS_CONFIG_STAGED:
        return "STAGED";
    case RLS_CONFIG_LOCKED:
        return "LOCKED";
    case RLS_CONFIG_EMPTY:
    default:
        return "EMPTY";
    }
}
