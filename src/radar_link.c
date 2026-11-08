#include "rls/radar_link.h"

#include <string.h>

#define RLS_RADAR_STATUS_MASK 0x03ffu
#define RLS_RADAR_HEADER_MASK 0x0003u
#define RLS_RADAR_QUALITY_MASK 0x07ffu

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
    return (uint16_t)src[0] | (uint16_t)((uint16_t)src[1] << 8);
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

uint32_t rls_radar_crc32c(const uint8_t *data, size_t length)
{
    if (data == NULL && length != 0u) {
        return 0u;
    }
    uint32_t crc = 0xffffffffu;
    for (size_t i = 0u; i < length; ++i) {
        crc ^= data[i];
        for (unsigned int bit = 0u; bit < 8u; ++bit) {
            const uint32_t mask = 0u - (crc & 1u);
            crc = (crc >> 1) ^ (0x82f63b78u & mask);
        }
    }
    return ~crc;
}

uint16_t rls_radar_link_expected_payload_length(uint8_t type)
{
    switch (type) {
    case RLS_RADAR_MSG_HEARTBEAT:
    case RLS_RADAR_MSG_MEASUREMENT:
    case RLS_RADAR_MSG_HEALTH:
    case RLS_RADAR_MSG_CARRIER_HEARTBEAT:
        return 36u;
    case RLS_RADAR_MSG_SERVICE_ACK:
    case RLS_RADAR_MSG_SERVICE_REQUEST:
        return RLS_RADAR_SERVICE_PAYLOAD_SIZE;
    default:
        return 0u;
    }
}

int rls_radar_link_is_valid_type(uint8_t type)
{
    return rls_radar_link_expected_payload_length(type) != 0u;
}

int rls_radar_link_encode(
    const rls_radar_link_frame_t *frame,
    uint8_t *wire,
    size_t wire_size)
{
    if (frame == NULL || wire == NULL) {
        return RLS_RADAR_LINK_ERROR_ARGUMENT;
    }
    if (wire_size != RLS_RADAR_LINK_WIRE_SIZE) {
        return RLS_RADAR_LINK_ERROR_WIRE_SIZE;
    }
    if (frame->version != RLS_RADAR_LINK_VERSION) {
        return RLS_RADAR_LINK_ERROR_VERSION;
    }
    if (!rls_radar_link_is_valid_type(frame->type)) {
        return RLS_RADAR_LINK_ERROR_TYPE;
    }
    if (frame->payload_length != rls_radar_link_expected_payload_length(frame->type)) {
        return RLS_RADAR_LINK_ERROR_PAYLOAD_LENGTH;
    }
    if ((frame->status_flags & 0xfc00u) != 0u
        || (frame->header_flags & 0xfffcu) != 0u) {
        return RLS_RADAR_LINK_ERROR_RESERVED;
    }
    if (frame->session_id == 0u) {
        return RLS_RADAR_LINK_ERROR_SESSION;
    }

    memset(wire, 0, wire_size);
    wire[0] = frame->version;
    wire[1] = frame->type;
    put_u16_le(&wire[2], frame->status_flags);
    put_u32_le(&wire[4], frame->sequence);
    put_u64_le(&wire[8], frame->timestamp_us);
    put_u32_le(&wire[16], frame->session_id);
    put_u16_le(&wire[20], frame->payload_length);
    put_u16_le(&wire[22], frame->header_flags);
    memcpy(&wire[24], frame->payload, frame->payload_length);
    put_u32_le(&wire[RLS_RADAR_LINK_CRC_OFFSET],
        rls_radar_crc32c(wire, RLS_RADAR_LINK_CRC_OFFSET));
    return RLS_RADAR_LINK_OK;
}

int rls_radar_link_decode(
    const uint8_t *wire,
    size_t wire_size,
    rls_radar_link_frame_t *frame)
{
    if (wire == NULL || frame == NULL) {
        return RLS_RADAR_LINK_ERROR_ARGUMENT;
    }
    if (wire_size != RLS_RADAR_LINK_WIRE_SIZE) {
        return RLS_RADAR_LINK_ERROR_WIRE_SIZE;
    }
    const uint32_t received_crc = get_u32_le(&wire[RLS_RADAR_LINK_CRC_OFFSET]);
    if (received_crc != rls_radar_crc32c(wire, RLS_RADAR_LINK_CRC_OFFSET)) {
        return RLS_RADAR_LINK_ERROR_CRC;
    }
    if (wire[0] != RLS_RADAR_LINK_VERSION) {
        return RLS_RADAR_LINK_ERROR_VERSION;
    }
    if (!rls_radar_link_is_valid_type(wire[1])) {
        return RLS_RADAR_LINK_ERROR_TYPE;
    }
    const uint16_t payload_length = get_u16_le(&wire[20]);
    if (payload_length != rls_radar_link_expected_payload_length(wire[1])) {
        return RLS_RADAR_LINK_ERROR_PAYLOAD_LENGTH;
    }
    const uint16_t status_flags = get_u16_le(&wire[2]);
    const uint16_t header_flags = get_u16_le(&wire[22]);
    if ((status_flags & 0xfc00u) != 0u
        || (header_flags & 0xfffcu) != 0u) {
        return RLS_RADAR_LINK_ERROR_RESERVED;
    }
    const uint32_t session_id = get_u32_le(&wire[16]);
    if (session_id == 0u) {
        return RLS_RADAR_LINK_ERROR_SESSION;
    }
    for (size_t i = payload_length; i < RLS_RADAR_LINK_PAYLOAD_SIZE; ++i) {
        if (wire[24u + i] != 0u) {
            return RLS_RADAR_LINK_ERROR_RESERVED;
        }
    }

    memset(frame, 0, sizeof(*frame));
    frame->version = wire[0];
    frame->type = wire[1];
    frame->status_flags = status_flags;
    frame->sequence = get_u32_le(&wire[4]);
    frame->timestamp_us = get_u64_le(&wire[8]);
    frame->session_id = session_id;
    frame->payload_length = payload_length;
    frame->header_flags = header_flags;
    memcpy(frame->payload, &wire[24], payload_length);
    return RLS_RADAR_LINK_OK;
}

static bool measurement_invalid_fields_are_zero(
    const rls_radar_measurement_t *measurement)
{
    if ((measurement->quality_flags & RLS_RADAR_QUALITY_RANGE_VALID) == 0u
        && measurement->range_mm != 0u) {
        return false;
    }
    if ((measurement->quality_flags & RLS_RADAR_QUALITY_VELOCITY_VALID) == 0u
        && measurement->radial_velocity_mm_s != 0) {
        return false;
    }
    if ((measurement->quality_flags & RLS_RADAR_QUALITY_AZIMUTH_VALID) == 0u
        && measurement->azimuth_mdeg != 0) {
        return false;
    }
    if ((measurement->quality_flags & RLS_RADAR_QUALITY_ELEVATION_VALID) == 0u
        && measurement->elevation_mdeg != 0) {
        return false;
    }
    if ((measurement->quality_flags & RLS_RADAR_QUALITY_SNR_VALID) == 0u
        && measurement->snr_cdb != 0) {
        return false;
    }
    if ((measurement->quality_flags & RLS_RADAR_QUALITY_RCS_VALID) == 0u
        && measurement->rcs_cdbsm != 0) {
        return false;
    }
    if ((measurement->quality_flags & RLS_RADAR_QUALITY_UNCERTAINTY_VALID) == 0u
        && (measurement->range_sigma_mm != 0u
            || measurement->velocity_sigma_mm_s != 0u
            || measurement->azimuth_sigma_mdeg != 0u
            || measurement->elevation_sigma_mdeg != 0u)) {
        return false;
    }
    return true;
}

static bool measurement_is_valid(const rls_radar_measurement_t *measurement)
{
    if ((measurement->quality_flags & 0xf800u) != 0u
        || measurement->track_state > RLS_RADAR_TRACK_LOST) {
        return false;
    }
    if (measurement->target_id == 0u) {
        if (measurement->track_state != RLS_RADAR_TRACK_NONE
            || measurement->quality_flags != 0u) {
            return false;
        }
    } else if (measurement->track_state == RLS_RADAR_TRACK_NONE) {
        return false;
    }
    return measurement_invalid_fields_are_zero(measurement);
}

static bool service_operation_is_valid(uint8_t operation)
{
    return operation >= RLS_RADAR_SERVICE_START_OBSERVATION
        && operation <= RLS_RADAR_SERVICE_RESET_STATISTICS;
}

static bool bytes_are_zero(const uint8_t *data, size_t begin, size_t end)
{
    for (size_t i = begin; i < end; ++i) {
        if (data[i] != 0u) {
            return false;
        }
    }
    return true;
}

int rls_radar_measurement_pack(
    const rls_radar_measurement_t *measurement,
    rls_radar_link_frame_t *frame)
{
    if (measurement == NULL || frame == NULL) {
        return RLS_RADAR_LINK_ERROR_ARGUMENT;
    }
    if (!measurement_is_valid(measurement)) {
        return RLS_RADAR_LINK_ERROR_PAYLOAD;
    }
    frame->type = RLS_RADAR_MSG_MEASUREMENT;
    frame->payload_length = RLS_RADAR_LINK_PAYLOAD_SIZE;
    memset(frame->payload, 0, sizeof(frame->payload));
    put_u32_le(&frame->payload[0], measurement->target_id);
    put_u32_le(&frame->payload[4], measurement->range_mm);
    put_u32_le(&frame->payload[8], (uint32_t)measurement->radial_velocity_mm_s);
    put_u32_le(&frame->payload[12], (uint32_t)measurement->azimuth_mdeg);
    put_u32_le(&frame->payload[16], (uint32_t)measurement->elevation_mdeg);
    put_u16_le(&frame->payload[20], (uint16_t)measurement->snr_cdb);
    put_u16_le(&frame->payload[22], (uint16_t)measurement->rcs_cdbsm);
    put_u16_le(&frame->payload[24], measurement->range_sigma_mm);
    put_u16_le(&frame->payload[26], measurement->velocity_sigma_mm_s);
    put_u16_le(&frame->payload[28], measurement->azimuth_sigma_mdeg);
    put_u16_le(&frame->payload[30], measurement->elevation_sigma_mdeg);
    put_u16_le(&frame->payload[32], measurement->quality_flags);
    frame->payload[34] = measurement->track_state;
    return RLS_RADAR_LINK_OK;
}

int rls_radar_measurement_unpack(
    const rls_radar_link_frame_t *frame,
    rls_radar_measurement_t *measurement)
{
    if (frame == NULL || measurement == NULL) {
        return RLS_RADAR_LINK_ERROR_ARGUMENT;
    }
    if (frame->type != RLS_RADAR_MSG_MEASUREMENT
        || frame->payload_length != RLS_RADAR_LINK_PAYLOAD_SIZE
        || frame->payload[35] != 0u) {
        return RLS_RADAR_LINK_ERROR_PAYLOAD;
    }
    measurement->target_id = get_u32_le(&frame->payload[0]);
    measurement->range_mm = get_u32_le(&frame->payload[4]);
    measurement->radial_velocity_mm_s = (int32_t)get_u32_le(&frame->payload[8]);
    measurement->azimuth_mdeg = (int32_t)get_u32_le(&frame->payload[12]);
    measurement->elevation_mdeg = (int32_t)get_u32_le(&frame->payload[16]);
    measurement->snr_cdb = (int16_t)get_u16_le(&frame->payload[20]);
    measurement->rcs_cdbsm = (int16_t)get_u16_le(&frame->payload[22]);
    measurement->range_sigma_mm = get_u16_le(&frame->payload[24]);
    measurement->velocity_sigma_mm_s = get_u16_le(&frame->payload[26]);
    measurement->azimuth_sigma_mdeg = get_u16_le(&frame->payload[28]);
    measurement->elevation_sigma_mdeg = get_u16_le(&frame->payload[30]);
    measurement->quality_flags = get_u16_le(&frame->payload[32]);
    measurement->track_state = frame->payload[34];
    return measurement_is_valid(measurement)
        ? RLS_RADAR_LINK_OK
        : RLS_RADAR_LINK_ERROR_PAYLOAD;
}

int rls_radar_service_request_pack(
    const rls_radar_service_request_t *request,
    rls_radar_link_frame_t *frame)
{
    if (request == NULL || frame == NULL) {
        return RLS_RADAR_LINK_ERROR_ARGUMENT;
    }
    if (!service_operation_is_valid(request->operation)
        || request->request_id == 0u) {
        return RLS_RADAR_LINK_ERROR_PAYLOAD;
    }
    frame->type = RLS_RADAR_MSG_SERVICE_REQUEST;
    frame->payload_length = RLS_RADAR_SERVICE_PAYLOAD_SIZE;
    frame->header_flags = RLS_RADAR_HEADER_ACK_REQUIRED;
    memset(frame->payload, 0, sizeof(frame->payload));
    frame->payload[0] = request->operation;
    put_u32_le(&frame->payload[4], request->request_id);
    return RLS_RADAR_LINK_OK;
}

int rls_radar_service_request_unpack(
    const rls_radar_link_frame_t *frame,
    rls_radar_service_request_t *request)
{
    if (frame == NULL || request == NULL) {
        return RLS_RADAR_LINK_ERROR_ARGUMENT;
    }
    if (frame->type != RLS_RADAR_MSG_SERVICE_REQUEST
        || frame->payload_length != RLS_RADAR_SERVICE_PAYLOAD_SIZE
        || frame->header_flags != RLS_RADAR_HEADER_ACK_REQUIRED
        || !service_operation_is_valid(frame->payload[0])
        || !bytes_are_zero(frame->payload, 1u, 4u)
        || !bytes_are_zero(frame->payload, 8u, RLS_RADAR_SERVICE_PAYLOAD_SIZE)) {
        return RLS_RADAR_LINK_ERROR_PAYLOAD;
    }
    request->operation = frame->payload[0];
    request->request_id = get_u32_le(&frame->payload[4]);
    return request->request_id != 0u
        ? RLS_RADAR_LINK_OK
        : RLS_RADAR_LINK_ERROR_PAYLOAD;
}

int rls_radar_service_ack_pack(
    const rls_radar_service_ack_t *ack,
    rls_radar_link_frame_t *frame)
{
    if (ack == NULL || frame == NULL) {
        return RLS_RADAR_LINK_ERROR_ARGUMENT;
    }
    if (!service_operation_is_valid(ack->operation)
        || ack->status > RLS_RADAR_SERVICE_ACK_INTERNAL_ERROR
        || ack->request_id == 0u) {
        return RLS_RADAR_LINK_ERROR_PAYLOAD;
    }
    frame->type = RLS_RADAR_MSG_SERVICE_ACK;
    frame->payload_length = RLS_RADAR_SERVICE_PAYLOAD_SIZE;
    frame->header_flags = RLS_RADAR_HEADER_ACK_RESPONSE;
    memset(frame->payload, 0, sizeof(frame->payload));
    frame->payload[0] = ack->operation;
    frame->payload[1] = ack->status;
    put_u32_le(&frame->payload[4], ack->request_id);
    return RLS_RADAR_LINK_OK;
}

int rls_radar_service_ack_unpack(
    const rls_radar_link_frame_t *frame,
    rls_radar_service_ack_t *ack)
{
    if (frame == NULL || ack == NULL) {
        return RLS_RADAR_LINK_ERROR_ARGUMENT;
    }
    if (frame->type != RLS_RADAR_MSG_SERVICE_ACK
        || frame->payload_length != RLS_RADAR_SERVICE_PAYLOAD_SIZE
        || frame->header_flags != RLS_RADAR_HEADER_ACK_RESPONSE
        || !service_operation_is_valid(frame->payload[0])
        || frame->payload[1] > RLS_RADAR_SERVICE_ACK_INTERNAL_ERROR
        || !bytes_are_zero(frame->payload, 2u, 4u)
        || !bytes_are_zero(frame->payload, 8u, RLS_RADAR_SERVICE_PAYLOAD_SIZE)) {
        return RLS_RADAR_LINK_ERROR_PAYLOAD;
    }
    ack->operation = frame->payload[0];
    ack->status = frame->payload[1];
    ack->request_id = get_u32_le(&frame->payload[4]);
    return ack->request_id != 0u
        ? RLS_RADAR_LINK_OK
        : RLS_RADAR_LINK_ERROR_PAYLOAD;
}

void rls_radar_sequence_tracker_init(rls_radar_sequence_tracker_t *tracker)
{
    if (tracker != NULL) {
        memset(tracker, 0, sizeof(*tracker));
    }
}

rls_radar_sequence_result_t rls_radar_sequence_check(
    rls_radar_sequence_tracker_t *tracker,
    uint32_t session_id,
    uint32_t sequence)
{
    if (tracker == NULL || session_id == 0u) {
        return RLS_RADAR_SEQUENCE_INVALID_SESSION;
    }
    if (!tracker->initialized) {
        tracker->initialized = true;
        tracker->session_id = session_id;
        tracker->last_sequence = sequence;
        return RLS_RADAR_SEQUENCE_FIRST;
    }
    if (tracker->session_id != session_id) {
        tracker->session_id = session_id;
        tracker->last_sequence = sequence;
        return RLS_RADAR_SEQUENCE_NEW_SESSION;
    }
    const uint32_t delta = sequence - tracker->last_sequence;
    if (delta == 0u) {
        return RLS_RADAR_SEQUENCE_DUPLICATE;
    }
    if (delta > 0x7fffffffu) {
        return RLS_RADAR_SEQUENCE_STALE;
    }
    tracker->last_sequence = sequence;
    return delta == 1u ? RLS_RADAR_SEQUENCE_NEXT : RLS_RADAR_SEQUENCE_GAP;
}
