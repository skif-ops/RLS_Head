#include "rls/config_lock.h"

#include <stdint.h>
#include <stdlib.h>

#define CHECK(expr) do { if (!(expr)) abort(); } while (0)

static void test_known_crc32_vector(void)
{
    static const uint8_t data[] = {
        '1','2','3','4','5','6','7','8','9'
    };

    CHECK(
        rls_config_crc32(
            data,
            sizeof(data)
        )
        == UINT32_C(0xCBF43926)
    );
}

static void test_stage_commit_verify(void)
{
    static const uint8_t config[] = {
        0x10u, 0x20u, 0x30u, 0x40u
    };

    rls_config_lock_t lock;
    rls_config_lock_init(&lock);

    CHECK(lock.state == RLS_CONFIG_EMPTY);

    CHECK(
        rls_config_lock_stage(
            &lock,
            3u,
            config,
            sizeof(config)
        )
    );

    CHECK(lock.state == RLS_CONFIG_STAGED);
    CHECK(lock.version == 3u);
    CHECK(lock.length == sizeof(config));

    CHECK(
        rls_config_lock_commit(
            &lock
        )
    );

    CHECK(
        rls_config_lock_verify(
            &lock,
            3u,
            config,
            sizeof(config)
        )
    );
}

static void test_locked_config_is_immutable_until_reset(void)
{
    static const uint8_t config_a[] = {1u, 2u};
    static const uint8_t config_b[] = {1u, 3u};

    rls_config_lock_t lock;
    rls_config_lock_init(&lock);

    CHECK(
        rls_config_lock_stage(
            &lock,
            1u,
            config_a,
            sizeof(config_a)
        )
    );
    CHECK(
        rls_config_lock_commit(
            &lock
        )
    );

    CHECK(
        !rls_config_lock_stage(
            &lock,
            2u,
            config_b,
            sizeof(config_b)
        )
    );

    CHECK(
        !rls_config_lock_verify(
            &lock,
            1u,
            config_b,
            sizeof(config_b)
        )
    );

    CHECK(
        rls_config_lock_reset(
            &lock
        )
    );

    CHECK(
        rls_config_lock_stage(
            &lock,
            2u,
            config_b,
            sizeof(config_b)
        )
    );
}

int main(void)
{
    test_known_crc32_vector();
    test_stage_commit_verify();
    test_locked_config_is_immutable_until_reset();
    return 0;
}
