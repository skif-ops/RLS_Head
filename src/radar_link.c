#include "rls/radar_link.h"

static void put_u16_le(uint8_t *dst, uint16_t value)
{
    dst[0] = (uint8_t)(value & 0xffu);
    dst[1] = (uint8_t)((value >> 8) & 0xffu);
}

static void put_u32_le(uint8_t *dst, uint32_t value)
{
    dst[0] = (uint8_t)(value & 0xffu);
    dst[1] = (uint8_t)((value >> 8) & 0xffu);
    dst[2] = (uint8_t)((value >> 16) & 0xffu);
    dst[3] = (uint8_t)((value >> 24) & 0xffu);
}

static void put_u64_le(uint8_t *dst, uint64_t value)
{
    for (unsigned int i = 0; i < 8u; ++i) {
        dst[i] = (uint8_t)((value >> (8u * i)) & 0xffu);
    }
}

static uint16_t get_u16_le(const uint8_t *src)
{
    return (uint16_t)src[0]
        | (uint16_t)((uint16_t)src[1] << 8);
}

static uint32_t get_u32_le(const uint8_t *src)
{
    return (uint32_t)src[0]
        | ((uint32_t)src[1] << 8)
        | ((uint32_t)src[2] << 16)
        | ((uint32_t)src[3] << 24);
}

static uint64_t get_u64_le(const uint8_t *src)
{
    uint64_t value = 0u;

    for (unsigned int i = 0; i < 8u; ++i) {
        value |= ((uint64_t)src[i]) << (8u * i);
    }

    return value;
}

int rls_radar_link_is_valid_type(uint8_t type)
{
    return type == (uint8_t)RLS_RADAR_MSG_HEARTBEAT
        || type == (uint8_t)RLS_RADAR_MSG_FRAME_META
        || type == (uint8_t)RLS_RADAR_MSG_HEALTH;
}

int rls_radar_link_encode(
    const rls_radar_link_msg_t *msg,
    uint8_t *wire,
    size_t wire_size
)
{
    if (msg == NULL || wire == NULL) {
        return -1;
    }

    if (wire_size < RLS_RADAR_LINK_WIRE_SIZE) {
        return -2;
    }

    if (msg->version != RLS_RADAR_LINK_VERSION) {
        return -3;
    }

    if (!rls_radar_link_is_valid_type(msg->type)) {
        return -4;
    }

    wire[0] = msg->version;
    wire[1] = msg->type;
    put_u16_le(&wire[2], msg->status_flags);
    put_u32_le(&wire[4], msg->sequence);
    put_u64_le(&wire[8], msg->radar_time_us);
    put_u32_le(&wire[16], msg->config_crc32);
    put_u16_le(&wire[20], (uint16_t)msg->temperature_cdeg);
    put_u16_le(&wire[22], msg->measurement_count);

    return 0;
}

int rls_radar_link_decode(
    const uint8_t *wire,
    size_t wire_size,
    rls_radar_link_msg_t *msg
)
{
    if (wire == NULL || msg == NULL) {
        return -1;
    }

    if (wire_size != RLS_RADAR_LINK_WIRE_SIZE) {
        return -2;
    }

    if (wire[0] != RLS_RADAR_LINK_VERSION) {
        return -3;
    }

    if (!rls_radar_link_is_valid_type(wire[1])) {
        return -4;
    }

    msg->version = wire[0];
    msg->type = wire[1];
    msg->status_flags = get_u16_le(&wire[2]);
    msg->sequence = get_u32_le(&wire[4]);
    msg->radar_time_us = get_u64_le(&wire[8]);
    msg->config_crc32 = get_u32_le(&wire[16]);
    msg->temperature_cdeg = (int16_t)get_u16_le(&wire[20]);
    msg->measurement_count = get_u16_le(&wire[22]);

    return 0;
}
