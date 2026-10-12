#include "rls/radar_link.h"

#include <stdint.h>
#include <string.h>

static int test_round_trip(void)
{
    rls_radar_link_msg_t input = {
        .version = RLS_RADAR_LINK_VERSION,
        .type = RLS_RADAR_MSG_FRAME_META,
        .status_flags = 0x1234u,
        .sequence = 0x01020304u,
        .radar_time_us = UINT64_C(0x0102030405060708),
        .config_crc32 = 0x89abcdefu,
        .temperature_cdeg = -125,
        .measurement_count = 17u,
    };
    rls_radar_link_msg_t output;
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE];

    memset(&output, 0, sizeof(output));
    memset(wire, 0, sizeof(wire));

    if (rls_radar_link_encode(&input, wire, sizeof(wire)) != 0) {
        return 1;
    }

    if (rls_radar_link_decode(wire, sizeof(wire), &output) != 0) {
        return 2;
    }

    if (
        output.version != input.version
        || output.type != input.type
        || output.status_flags != input.status_flags
        || output.sequence != input.sequence
        || output.radar_time_us != input.radar_time_us
        || output.config_crc32 != input.config_crc32
        || output.temperature_cdeg != input.temperature_cdeg
        || output.measurement_count != input.measurement_count
    ) {
        return 3;
    }

    return 0;
}

static int test_rejects_invalid_type(void)
{
    rls_radar_link_msg_t msg = {
        .version = RLS_RADAR_LINK_VERSION,
        .type = 99u,
    };
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE];

    return (
        rls_radar_link_encode(
            &msg,
            wire,
            sizeof(wire)
        ) == -4
    ) ? 0 : 1;
}

static int test_rejects_wrong_wire_size(void)
{
    rls_radar_link_msg_t msg;
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE] = {0};

    wire[0] = RLS_RADAR_LINK_VERSION;
    wire[1] = RLS_RADAR_MSG_HEARTBEAT;

    return (
        rls_radar_link_decode(
            wire,
            RLS_RADAR_LINK_WIRE_SIZE - 1u,
            &msg
        ) == -2
    ) ? 0 : 1;
}

int main(void)
{
    if (test_round_trip() != 0) {
        return 1;
    }

    if (test_rejects_invalid_type() != 0) {
        return 2;
    }

    if (test_rejects_wrong_wire_size() != 0) {
        return 3;
    }

    return 0;
}
