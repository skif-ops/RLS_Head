#ifndef RLS_RADAR_LINK_H
#define RLS_RADAR_LINK_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RLS_RADAR_LINK_VERSION 1u
#define RLS_RADAR_LINK_WIRE_SIZE 64u
#define RLS_RADAR_LINK_PAYLOAD_SIZE 36u
#define RLS_RADAR_LINK_CRC_OFFSET 60u

#define RLS_RADAR_CAN_AWR_TO_CARRIER_ID 0x320u
#define RLS_RADAR_CAN_CARRIER_TO_AWR_ID 0x321u

#define RLS_RADAR_MEASUREMENT_TIMEOUT_US UINT64_C(250000)
#define RLS_RADAR_HEARTBEAT_DEGRADED_US UINT64_C(300000)
#define RLS_RADAR_LINK_LOST_US UINT64_C(500000)
#define RLS_RADAR_SERVICE_ACK_TIMEOUT_US UINT64_C(500000)
#define RLS_RADAR_BUS_OFF_RESTART_DELAY_US UINT64_C(100000)

typedef enum {
    RLS_RADAR_MSG_HEARTBEAT = 0x01,
    RLS_RADAR_MSG_MEASUREMENT = 0x02,
    RLS_RADAR_MSG_HEALTH = 0x03,
    RLS_RADAR_MSG_SERVICE_ACK = 0x04,
    RLS_RADAR_MSG_CARRIER_HEARTBEAT = 0x81,
    RLS_RADAR_MSG_SERVICE_REQUEST = 0x82
} rls_radar_msg_type_t;

typedef enum {
    RLS_RADAR_STATUS_DATA_VALID = 1u << 0,
    RLS_RADAR_STATUS_DEGRADED = 1u << 1,
    RLS_RADAR_STATUS_CONFIG_MATCH = 1u << 2,
    RLS_RADAR_STATUS_TIME_VALID = 1u << 3,
    RLS_RADAR_STATUS_CALIBRATION_VALID = 1u << 4,
    RLS_RADAR_STATUS_BUS_OFF_RECOVERED = 1u << 5,
    RLS_RADAR_STATUS_RX_CRC_ERROR = 1u << 6,
    RLS_RADAR_STATUS_RX_SEQUENCE_GAP = 1u << 7,
    RLS_RADAR_STATUS_PEER_LOST = 1u << 8,
    RLS_RADAR_STATUS_RADAR_FAULT = 1u << 9
} rls_radar_status_flag_t;

typedef enum {
    RLS_RADAR_HEADER_ACK_REQUIRED = 1u << 0,
    RLS_RADAR_HEADER_ACK_RESPONSE = 1u << 1
} rls_radar_header_flag_t;

typedef enum {
    RLS_RADAR_QUALITY_RANGE_VALID = 1u << 0,
    RLS_RADAR_QUALITY_VELOCITY_VALID = 1u << 1,
    RLS_RADAR_QUALITY_AZIMUTH_VALID = 1u << 2,
    RLS_RADAR_QUALITY_ELEVATION_VALID = 1u << 3,
    RLS_RADAR_QUALITY_SNR_VALID = 1u << 4,
    RLS_RADAR_QUALITY_RCS_VALID = 1u << 5,
    RLS_RADAR_QUALITY_UNCERTAINTY_VALID = 1u << 6,
    RLS_RADAR_QUALITY_TRACK_CONFIRMED = 1u << 7,
    RLS_RADAR_QUALITY_MULTIPATH_SUSPECT = 1u << 8,
    RLS_RADAR_QUALITY_SATURATED = 1u << 9,
    RLS_RADAR_QUALITY_CALIBRATION_VALID = 1u << 10
} rls_radar_quality_flag_t;

typedef enum {
    RLS_RADAR_TRACK_NONE = 0,
    RLS_RADAR_TRACK_TENTATIVE = 1,
    RLS_RADAR_TRACK_CONFIRMED = 2,
    RLS_RADAR_TRACK_COASTING = 3,
    RLS_RADAR_TRACK_LOST = 4
} rls_radar_track_state_t;

typedef enum {
    RLS_RADAR_SERVICE_START_OBSERVATION = 1,
    RLS_RADAR_SERVICE_STOP_OBSERVATION = 2,
    RLS_RADAR_SERVICE_RESET_STATISTICS = 3
} rls_radar_service_operation_t;

typedef enum {
    RLS_RADAR_SEQUENCE_FIRST = 0,
    RLS_RADAR_SEQUENCE_NEXT = 1,
    RLS_RADAR_SEQUENCE_GAP = 2,
    RLS_RADAR_SEQUENCE_NEW_SESSION = 3,
    RLS_RADAR_SEQUENCE_DUPLICATE = -1,
    RLS_RADAR_SEQUENCE_STALE = -2,
    RLS_RADAR_SEQUENCE_INVALID_SESSION = -3
} rls_radar_sequence_result_t;

typedef enum {
    RLS_RADAR_LINK_OK = 0,
    RLS_RADAR_LINK_ERROR_ARGUMENT = -1,
    RLS_RADAR_LINK_ERROR_WIRE_SIZE = -2,
    RLS_RADAR_LINK_ERROR_CRC = -3,
    RLS_RADAR_LINK_ERROR_VERSION = -4,
    RLS_RADAR_LINK_ERROR_TYPE = -5,
    RLS_RADAR_LINK_ERROR_PAYLOAD_LENGTH = -6,
    RLS_RADAR_LINK_ERROR_RESERVED = -7,
    RLS_RADAR_LINK_ERROR_SESSION = -8,
    RLS_RADAR_LINK_ERROR_PAYLOAD = -9
} rls_radar_link_result_t;

typedef struct {
    uint8_t version;
    uint8_t type;
    uint16_t status_flags;
    uint32_t sequence;
    uint64_t timestamp_us;
    uint32_t session_id;
    uint16_t payload_length;
    uint16_t header_flags;
    uint8_t payload[RLS_RADAR_LINK_PAYLOAD_SIZE];
} rls_radar_link_frame_t;

typedef struct {
    uint32_t target_id;
    uint32_t range_mm;
    int32_t radial_velocity_mm_s;
    int32_t azimuth_mdeg;
    int32_t elevation_mdeg;
    int16_t snr_cdb;
    int16_t rcs_cdbsm;
    uint16_t range_sigma_mm;
    uint16_t velocity_sigma_mm_s;
    uint16_t azimuth_sigma_mdeg;
    uint16_t elevation_sigma_mdeg;
    uint16_t quality_flags;
    uint8_t track_state;
} rls_radar_measurement_t;

typedef struct {
    bool initialized;
    uint32_t session_id;
    uint32_t last_sequence;
} rls_radar_sequence_tracker_t;

uint32_t rls_radar_crc32c(const uint8_t *data, size_t length);

int rls_radar_link_encode(
    const rls_radar_link_frame_t *frame,
    uint8_t *wire,
    size_t wire_size
);

int rls_radar_link_decode(
    const uint8_t *wire,
    size_t wire_size,
    rls_radar_link_frame_t *frame
);

int rls_radar_measurement_pack(
    const rls_radar_measurement_t *measurement,
    rls_radar_link_frame_t *frame
);

int rls_radar_measurement_unpack(
    const rls_radar_link_frame_t *frame,
    rls_radar_measurement_t *measurement
);

void rls_radar_sequence_tracker_init(rls_radar_sequence_tracker_t *tracker);

rls_radar_sequence_result_t rls_radar_sequence_check(
    rls_radar_sequence_tracker_t *tracker,
    uint32_t session_id,
    uint32_t sequence
);

uint16_t rls_radar_link_expected_payload_length(uint8_t type);
int rls_radar_link_is_valid_type(uint8_t type);

#ifdef __cplusplus
}
#endif

#endif
