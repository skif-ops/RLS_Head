#include "evt_fusion.h"
#include "evt_transport.h"
#include "rls/hil_r1.h"

#include <stdio.h>
#include <string.h>

#define CHECK(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return 1; \
    } \
} while (0)

#define VALID_DETECTION_FIELDS 0x7fu

static void write_u16(uint8_t **p, uint16_t value)
{
    *(*p)++ = (uint8_t)value;
    *(*p)++ = (uint8_t)(value >> 8);
}

static void write_u32(uint8_t **p, uint32_t value)
{
    *(*p)++ = (uint8_t)value;
    *(*p)++ = (uint8_t)(value >> 8);
    *(*p)++ = (uint8_t)(value >> 16);
    *(*p)++ = (uint8_t)(value >> 24);
}

static void write_u64(uint8_t **p, uint64_t value)
{
    write_u32(p, (uint32_t)value);
    write_u32(p, (uint32_t)(value >> 32));
}

static void write_float(uint8_t **p, float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof(bits));
    write_u32(p, bits);
}

static uint32_t read_u32(const uint8_t *p)
{
    return (uint32_t)p[0]
        | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16)
        | ((uint32_t)p[3] << 24);
}

static size_t make_radar_packet(uint8_t *packet, uint32_t sequence)
{
    const size_t total = HIL_HEADER_WIRE_SIZE
        + HIL_DETECTION_WIRE_SIZE + HIL_CRC_WIRE_SIZE;
    uint8_t *p = packet;
    write_u32(&p, HIL_PROTOCOL_MAGIC);
    write_u16(&p, HIL_SCHEMA_MAJOR);
    write_u16(&p, HIL_SCHEMA_MINOR);
    write_u32(&p, sequence);
    write_u32(&p, 10u);
    write_u64(&p, 1000000u);
    write_u16(&p, 1u);
    write_u16(&p, 0u);
    write_u32(&p, HIL_DETECTION_WIRE_SIZE);
    write_u32(&p, 7u);
    write_float(&p, 100.0f);
    write_float(&p, 2.0f);
    write_float(&p, 0.1f);
    write_float(&p, 0.05f);
    for (unsigned i = 0u; i < 16u; ++i) {
        const bool diagonal = i == 0u || i == 5u || i == 10u || i == 15u;
        write_float(&p, diagonal ? 0.01f : 0.0f);
    }
    write_float(&p, 25.0f);
    write_float(&p, 0.95f);
    write_float(&p, 1.0f);
    write_u32(&p, VALID_DETECTION_FIELDS);
    write_u32(&p, 0u);
    write_u32(&p, crc32c_compute(packet, total - HIL_CRC_WIRE_SIZE));
    return (size_t)(p - packet);
}

int main(void)
{
    uint8_t radar[HIL_HEADER_WIRE_SIZE
        + HIL_DETECTION_WIRE_SIZE + HIL_CRC_WIRE_SIZE];
    const size_t radar_length = make_radar_packet(radar, 1u);
    CHECK(radar_length == sizeof(radar));

    evt_transport_rx_t transport;
    evt_transport_rx_init(&transport);
    const uint8_t *assembled = NULL;
    size_t assembled_length = 0u;
    uint16_t offset = 0u;
    while (offset < radar_length) {
        const size_t remaining = radar_length - offset;
        const uint8_t segment_length = remaining > EVT_CAN_PAYLOAD_SIZE
            ? EVT_CAN_PAYLOAD_SIZE : (uint8_t)remaining;
        uint8_t frame[EVT_CAN_FRAME_SIZE];
        CHECK(evt_transport_encode_segment(
            3u, offset, (uint16_t)radar_length,
            &radar[offset], segment_length, frame) != 0u);
        const evt_transport_result_t result = evt_transport_rx_accept(
            &transport, frame, &assembled, &assembled_length);
        offset = (uint16_t)(offset + segment_length);
        CHECK(result == (offset == radar_length
            ? EVT_TRANSPORT_COMPLETE : EVT_TRANSPORT_MORE));
    }
    CHECK(assembled_length == radar_length);
    CHECK(memcmp(assembled, radar, radar_length) == 0);

    evt_runtime_config_t config;
    evt_runtime_config_default(&config);
    evt_fusion_context_t fusion;
    CHECK(evt_fusion_init(&fusion, &config));
    icm42688p_sample_t sample;
    memset(&sample, 0, sizeof(sample));
    sample.angular_rate_rad_s[2] = 0.1f;
    evt_fusion_note_imu(&fusion, &sample, 1000000u);
    evt_fusion_update_status(
        &fusion, 1001000u, TIME_SERVICE_LOCKED, 1.5f, 0u, 0u);

    HilRuntime runtime;
    hil_runtime_init(&runtime, 0x45565431u, 0x10203040u);
    uint8_t targetstate[TARGETSTATE_PACKET_SIZE];
    size_t targetstate_length = 0u;
    CHECK(hil_runtime_process_packet_ex(
        &runtime,
        assembled,
        assembled_length,
        1000500u,
        1001000u,
        evt_fusion_apply,
        &fusion,
        targetstate,
        sizeof(targetstate),
        &targetstate_length) == HIL_RUNTIME_OK);
    CHECK(targetstate_length == TARGETSTATE_PACKET_SIZE);
    CHECK(read_u32(targetstate) == TARGETSTATE_MAGIC);
    CHECK(crc32c_compute(targetstate, 196u) == read_u32(&targetstate[196]));
    CHECK((read_u32(&targetstate[184]) & EVT_FUSION_IMU_FRESH) != 0u);
    CHECK((read_u32(&targetstate[184]) & EVT_FUSION_SYSERR_APPLIED) != 0u);
    CHECK((read_u32(&targetstate[188]) & TS_FLAG_TIME_VALID) != 0u);

    uint8_t corrupted[sizeof(radar)];
    memcpy(corrupted, radar, sizeof(corrupted));
    corrupted[HIL_HEADER_WIRE_SIZE + 4u] ^= 1u;
    HilRuntime corrupt_runtime;
    hil_runtime_init(&corrupt_runtime, 1u, 1u);
    targetstate_length = 99u;
    CHECK(hil_runtime_process_packet_ex(
        &corrupt_runtime,
        corrupted,
        sizeof(corrupted),
        1000500u,
        1001000u,
        evt_fusion_apply,
        &fusion,
        targetstate,
        sizeof(targetstate),
        &targetstate_length) == HIL_RUNTIME_PARSE_ERROR);
    CHECK(targetstate_length == 0u);
    CHECK(corrupt_runtime.diag.crc_errors == 1u);

    evt_transport_rx_init(&transport);
    uint8_t out_of_order[EVT_CAN_FRAME_SIZE];
    CHECK(evt_transport_encode_segment(
        4u, 10u, (uint16_t)radar_length,
        &radar[10], 10u, out_of_order) != 0u);
    CHECK(evt_transport_rx_accept(
        &transport, out_of_order, &assembled, &assembled_length)
        == EVT_TRANSPORT_REJECTED);

    puts("EVT end-to-end digital twin passed");
    return 0;
}
