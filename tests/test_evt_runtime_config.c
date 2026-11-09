#include "evt_runtime_config.h"

#include <math.h>
#include <stdio.h>

#define CHECK(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return 1; \
    } \
} while (0)

int main(void)
{
    evt_runtime_config_t config;
    evt_runtime_config_default(&config);
    CHECK(evt_runtime_config_validate(&config));
    CHECK(evt_runtime_config_crc32c(&config) != 0u);

    evt_config_store_t store;
    evt_config_store_init(&store);
    CHECK(evt_config_store_commit(&store, &config));

    evt_runtime_config_t loaded;
    uint32_t generation;
    CHECK(evt_config_store_load(&store, &loaded, &generation));
    CHECK(generation == 1u);
    CHECK(loaded.radar_timeout_us == config.radar_timeout_us);

    config.radar_timeout_us = 300000u;
    CHECK(evt_config_store_commit(&store, &config));
    CHECK(evt_config_store_load(&store, &loaded, &generation));
    CHECK(generation == 2u);
    CHECK(loaded.radar_timeout_us == 300000u);

    store.slots[1].crc32c ^= 1u;
    CHECK(evt_config_store_load(&store, &loaded, &generation));
    CHECK(generation == 1u);
    CHECK(loaded.radar_timeout_us == 250000u);

    store.slots[0].crc32c ^= 1u;
    CHECK(!evt_config_store_load(&store, &loaded, &generation));

    evt_runtime_config_default(&config);
    config.time_phase_sigma_us = NAN;
    CHECK(!evt_runtime_config_validate(&config));
    CHECK(!evt_config_store_commit(&store, &config));

    printf(
        "EVT redundant configuration tests passed; default CRC32C=%08x\n",
        evt_runtime_config_crc32c(&loaded));
    return 0;
}
