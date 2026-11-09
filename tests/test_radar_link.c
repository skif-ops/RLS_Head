#include "rls/radar_link.h"

#include <stdint.h>
#include <string.h>

#define CHECK(condition) do { if (!(condition)) return __LINE__; } while (0)

static void put_u32_le(uint8_t *dst, uint32_t value)
{
    dst[0] = (uint8_t)(value & 0xffu);
    dst[1] = (uint8_t)((value >> 8) & 0xffu);
    dst[2] = (uint8_t)((value >> 16) & 0xffu);
    dst[3] = (uint8_t)((value >> 24) & 0xffu);
}

static int test_crc32c_vector(void)
{
    static const uint8_t text[] = "123456789";
    CHECK(rls_radar_crc32c(text, sizeof(text) - 1u) == 0xe3069283u);
    return 0;
}

static int test_measurement_round_trip(void)
{
    rls_radar_measurement_t input = {
        .target_id = 17u,
        .range_mm = 300125u,
        .radial_velocity_mm_s = -2500,
        .azimuth_mdeg = 12345,
        .elevation_mdeg = -6789,
        .snr_cdb = 1850,
        .rcs_cdbsm = -2000,
        .range_sigma_mm = 125u,
        .velocity_sigma_mm_s = 75u,
        .azimuth_sigma_mdeg = 450u,
        .elevation_sigma_mdeg = 600u,
        .quality_flags =
            RLS_RADAR_QUALITY_RANGE_VALID
            | RLS_RADAR_QUALITY_VELOCITY_VALID
            | RLS_RADAR_QUALITY_AZIMUTH_VALID
            | RLS_RADAR_QUALITY_ELEVATION_VALID
            | RLS_RADAR_QUALITY_SNR_VALID
            | RLS_RADAR_QUALITY_RCS_VALID
            | RLS_RADAR_QUALITY_UNCERTAINTY_VALID
            | RLS_RADAR_QUALITY_TRACK_CONFIRMED
            | RLS_RADAR_QUALITY_CALIBRATION_VALID,
        .track_state = RLS_RADAR_TRACK_CONFIRMED,
    };
    rls_radar_link_frame_t frame;
    rls_radar_link_frame_t decoded;
    rls_radar_measurement_t output;
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE];

    memset(&frame, 0, sizeof(frame));
    memset(&decoded, 0, sizeof(decoded));
    memset(&output, 0, sizeof(output));
    frame.version = RLS_RADAR_LINK_VERSION;
    frame.status_flags =
        RLS_RADAR_STATUS_DATA_VALID
        | RLS_RADAR_STATUS_CONFIG_MATCH
        | RLS_RADAR_STATUS_TIME_VALID
        | RLS_RADAR_STATUS_CALIBRATION_VALID;
    frame.sequence = 0x01020304u;
    frame.timestamp_us = UINT64_C(0x0102030405060708);
    frame.session_id = 0xa1b2c3d4u;

    CHECK(rls_radar_measurement_pack(&input, &frame) == RLS_RADAR_LINK_OK);
    CHECK(rls_radar_link_encode(&frame, wire, sizeof(wire)) == RLS_RADAR_LINK_OK);
    CHECK(wire[4] == 0x04u && wire[5] == 0x03u
        && wire[6] == 0x02u && wire[7] == 0x01u);
    CHECK(wire[8] == 0x08u && wire[15] == 0x01u);
    CHECK(wire[16] == 0xd4u && wire[19] == 0xa1u);
    CHECK(wire[20] == 36u && wire[21] == 0u);
    CHECK(rls_radar_link_decode(wire, sizeof(wire), &decoded) == RLS_RADAR_LINK_OK);
    CHECK(rls_radar_measurement_unpack(&decoded, &output) == RLS_RADAR_LINK_OK);
    CHECK(memcmp(&input, &output, sizeof(input)) == 0);
    return 0;
}

static int test_crc_and_reserved_rejection(void)
{
    rls_radar_link_frame_t frame;
    rls_radar_link_frame_t decoded;
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE];

    memset(&frame, 0, sizeof(frame));
    frame.version = RLS_RADAR_LINK_VERSION;
    frame.type = RLS_RADAR_MSG_SERVICE_REQUEST;
    frame.session_id = 1u;
    frame.payload_length = 16u;
    frame.header_flags = RLS_RADAR_HEADER_ACK_REQUIRED;
    CHECK(rls_radar_link_encode(&frame, wire, sizeof(wire)) == RLS_RADAR_LINK_OK);

    wire[30] ^= 0x40u;
    CHECK(rls_radar_link_decode(wire, sizeof(wire), &decoded)
        == RLS_RADAR_LINK_ERROR_CRC);
    wire[30] ^= 0x40u;

    wire[50] = 1u;
    put_u32_le(&wire[RLS_RADAR_LINK_CRC_OFFSET],
        rls_radar_crc32c(wire, RLS_RADAR_LINK_CRC_OFFSET));
    CHECK(rls_radar_link_decode(wire, sizeof(wire), &decoded)
        == RLS_RADAR_LINK_ERROR_RESERVED);
    return 0;
}

static int test_measurement_validity_rules(void)
{
    rls_radar_measurement_t measurement;
    rls_radar_link_frame_t frame;

    memset(&measurement, 0, sizeof(measurement));
    memset(&frame, 0, sizeof(frame));
    measurement.range_mm = 1u;
    CHECK(rls_radar_measurement_pack(&measurement, &frame)
        == RLS_RADAR_LINK_ERROR_PAYLOAD);

    memset(&measurement, 0, sizeof(measurement));
    measurement.target_id = 1u;
    measurement.track_state = RLS_RADAR_TRACK_NONE;
    CHECK(rls_radar_measurement_pack(&measurement, &frame)
        == RLS_RADAR_LINK_ERROR_PAYLOAD);
    return 0;
}

static int test_service_request_and_ack_contract(void)
{
    rls_radar_link_frame_t frame;
    rls_radar_link_frame_t decoded;
    rls_radar_service_request_t request = {
        RLS_RADAR_SERVICE_START_OBSERVATION,
        0x12345678u
    };
    rls_radar_service_request_t decoded_request;
    rls_radar_service_ack_t ack = {
        RLS_RADAR_SERVICE_START_OBSERVATION,
        RLS_RADAR_SERVICE_ACK_OK,
        0x12345678u
    };
    rls_radar_service_ack_t decoded_ack;
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE];

    memset(&frame, 0, sizeof(frame));
    frame.version = RLS_RADAR_LINK_VERSION;
    frame.sequence = 7u;
    frame.timestamp_us = 1000u;
    frame.session_id = 2u;
    CHECK(rls_radar_service_request_pack(&request, &frame)
        == RLS_RADAR_LINK_OK);
    CHECK(rls_radar_link_encode(&frame, wire, sizeof(wire))
        == RLS_RADAR_LINK_OK);
    CHECK(rls_radar_link_decode(wire, sizeof(wire), &decoded)
        == RLS_RADAR_LINK_OK);
    CHECK(rls_radar_service_request_unpack(&decoded, &decoded_request)
        == RLS_RADAR_LINK_OK);
    CHECK(decoded_request.operation == request.operation);
    CHECK(decoded_request.request_id == request.request_id);

    memset(&frame, 0, sizeof(frame));
    frame.version = RLS_RADAR_LINK_VERSION;
    frame.sequence = 8u;
    frame.timestamp_us = 1001u;
    frame.session_id = 3u;
    CHECK(rls_radar_service_ack_pack(&ack, &frame) == RLS_RADAR_LINK_OK);
    CHECK(rls_radar_link_encode(&frame, wire, sizeof(wire))
        == RLS_RADAR_LINK_OK);
    CHECK(rls_radar_link_decode(wire, sizeof(wire), &decoded)
        == RLS_RADAR_LINK_OK);
    CHECK(rls_radar_service_ack_unpack(&decoded, &decoded_ack)
        == RLS_RADAR_LINK_OK);
    CHECK(decoded_ack.operation == ack.operation);
    CHECK(decoded_ack.status == ack.status);
    CHECK(decoded_ack.request_id == ack.request_id);

    decoded.payload[8] = 1u;
    CHECK(rls_radar_service_ack_unpack(&decoded, &decoded_ack)
        == RLS_RADAR_LINK_ERROR_PAYLOAD);
    request.request_id = 0u;
    CHECK(rls_radar_service_request_pack(&request, &frame)
        == RLS_RADAR_LINK_ERROR_PAYLOAD);
    return 0;
}

static int test_sequence_contract(void)
{
    rls_radar_sequence_tracker_t tracker;
    rls_radar_sequence_tracker_init(&tracker);
    CHECK(rls_radar_sequence_check(&tracker, 0u, 0u)
        == RLS_RADAR_SEQUENCE_INVALID_SESSION);
    CHECK(rls_radar_sequence_check(&tracker, 1u, 0xfffffffeu)
        == RLS_RADAR_SEQUENCE_FIRST);
    CHECK(rls_radar_sequence_check(&tracker, 1u, 0xffffffffu)
        == RLS_RADAR_SEQUENCE_NEXT);
    CHECK(rls_radar_sequence_check(&tracker, 1u, 0u)
        == RLS_RADAR_SEQUENCE_NEXT);
    CHECK(rls_radar_sequence_check(&tracker, 1u, 0u)
        == RLS_RADAR_SEQUENCE_DUPLICATE);
    CHECK(rls_radar_sequence_check(&tracker, 1u, 2u)
        == RLS_RADAR_SEQUENCE_GAP);
    CHECK(rls_radar_sequence_check(&tracker, 1u, 1u)
        == RLS_RADAR_SEQUENCE_STALE);
    CHECK(rls_radar_sequence_check(&tracker, 2u, 0u)
        == RLS_RADAR_SEQUENCE_NEW_SESSION);
    return 0;
}

int main(void)
{
    CHECK(test_crc32c_vector() == 0);
    CHECK(test_measurement_round_trip() == 0);
    CHECK(test_crc_and_reserved_rejection() == 0);
    CHECK(test_measurement_validity_rules() == 0);
    CHECK(test_service_request_and_ack_contract() == 0);
    CHECK(test_sequence_contract() == 0);
    return 0;
}
