#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define HIL_PROTOCOL_MAGIC 0x31445248u /* "HRD1" LE */
#define HIL_SCHEMA_MAJOR 1u
#define HIL_SCHEMA_MINOR 0u
#define HIL_HEADER_WIRE_SIZE 32u
#define HIL_DETECTION_WIRE_SIZE 104u
#define HIL_CRC_WIRE_SIZE 4u
#define HIL_MAX_DETECTIONS 32u

#define TARGETSTATE_MAGIC 0x31474C52u /* "RLG1" LE */
#define TARGETSTATE_MAJOR 1u
#define TARGETSTATE_MINOR 0u
#define TARGETSTATE_MSG_STATE 1u
#define TARGETSTATE_HEADER_SIZE 24u
#define TARGETSTATE_PAYLOAD_SIZE 172u
#define TARGETSTATE_CRC_SIZE 4u
#define TARGETSTATE_PACKET_SIZE 200u

enum {
    TS_FRAME_BODY_FRU = 1u,
    TS_MOTION_CV = 1u
};

enum {
    TS_VALID_RANGE      = 1u << 0,
    TS_VALID_RANGE_RATE = 1u << 1,
    TS_VALID_ANGLES     = 1u << 2,
    TS_VALID_POSITION   = 1u << 3,
    TS_VALID_VELOCITY   = 1u << 4,
    TS_VALID_ACCEL      = 1u << 5,
    TS_VALID_POS_COV    = 1u << 6,
    TS_VALID_VEL_COV    = 1u << 7,
    TS_VALID_SNR        = 1u << 8,
    TS_VALID_TIME       = 1u << 9
};

enum {
    TS_FLAG_MEASUREMENT_VALID = 1u << 0,
    TS_FLAG_PREDICTED_STATE   = 1u << 1,
    TS_FLAG_REACQUIRED        = 1u << 2,
    TS_FLAG_TIME_VALID        = 1u << 3,
    TS_FLAG_COV_VALID         = 1u << 4
};

typedef struct {
    uint32_t detection_id;
    float range_m;
    float range_rate_m_s;
    float azimuth_rad;
    float elevation_rad;
    float covariance[16];
    float snr_db;
    float quality;
    float timestamp_uncertainty_us;
    uint32_t validity_flags;
    uint32_t radar_flags;
} HilDetectionDecoded;

typedef struct {
    uint32_t sequence;
    uint32_t frame_id;
    uint64_t measurement_time_us;
    uint16_t detection_count;
    uint16_t flags;
    HilDetectionDecoded detections[HIL_MAX_DETECTIONS];
} HilFrameDecoded;

typedef enum {
    HIL_PARSE_OK = 0,
    HIL_PARSE_BAD_LENGTH,
    HIL_PARSE_BAD_MAGIC,
    HIL_PARSE_BAD_VERSION,
    HIL_PARSE_BAD_CRC,
    HIL_PARSE_TOO_MANY_DETECTIONS,
    HIL_PARSE_TRUNCATED,
    HIL_PARSE_INVALID_FLOAT
} HilParseResult;

typedef struct {
    uint64_t measurement_time_us;
    uint64_t receive_time_us;
    uint32_t frame_id;
    uint32_t detection_id;
    float range_m;
    float range_rate_m_s;
    float azimuth_rad;
    float elevation_rad;
    float covariance[16];
    float snr_db;
    float quality;
    float timestamp_uncertainty_us;
    uint32_t validity_flags;
    uint32_t radar_flags;
} RadarMeasurement;

typedef struct {
    uint64_t measurement_time_us;
    float position_m[3];
    float covariance[9];
    float range_rate_m_s;
    float range_rate_sigma_m_s;
    float quality;
    uint32_t flags;
} CartesianMeasurement;

typedef enum {
    TRACK_NONE = 0,
    TRACK_TENTATIVE,
    TRACK_CONFIRMED,
    TRACK_COASTING,
    TRACK_LOST
} TrackLifecycle;

typedef struct {
    float x[6];
    float P[36];
    uint64_t state_time_us;
    uint64_t last_measurement_time_us;
    uint32_t track_id;
    TrackLifecycle lifecycle;
    uint32_t valid_updates;
    uint32_t consecutive_misses;
} CvTrack;

typedef struct {
    uint32_t track_id;
    uint64_t state_time_us;
    uint64_t last_measurement_time_us;
    float position_m[3];
    float velocity_m_s[3];
    float acceleration_m_s2[3];
    float position_cov[9];
    float velocity_cov[9];
    uint32_t lifecycle;
} TrackState;

typedef struct {
    uint64_t measurement_timestamp_us;
    uint64_t state_timestamp_us;
    uint64_t publish_timestamp_us;
    uint32_t track_id;
    uint8_t coordinate_frame;
    uint8_t track_state;
    uint8_t motion_model;
    uint8_t reserved0;
    uint32_t validity_mask;
    float range_m;
    float range_rate_m_s;
    float azimuth_deg;
    float elevation_deg;
    float relative_position_m[3];
    float relative_velocity_m_s[3];
    float relative_accel_m_s2[3];
    float snr_db;
    float track_quality;
    float confidence;
    float measurement_age_ms;
    float position_cov_ut[6];
    float velocity_cov_ut[6];
    float timestamp_uncertainty_us;
    uint32_t radar_status;
    uint32_t fusion_status;
    uint32_t track_flags;
    uint32_t reserved1;
} TargetStateV1;

typedef struct {
    uint32_t frames_rx;
    uint32_t frames_valid;
    uint32_t crc_errors;
    uint32_t duplicate_count;
    uint32_t out_of_order_count;
    uint32_t frame_gap_count;
    uint32_t numeric_errors;
    uint32_t tracker_updates;
    uint32_t tracker_misses;
    uint32_t targetstate_tx;
} HilDiagnostics;

typedef struct {
    bool have_sequence;
    uint32_t last_sequence;
    bool have_track;
    CvTrack track;
    bool have_last_measurement;
    RadarMeasurement last_measurement;
    uint32_t next_track_id;
    uint32_t targetstate_sequence;
    uint32_t source_id;
    uint32_t boot_id;
    HilDiagnostics diag;
} HilRuntime;

typedef enum {
    HIL_RUNTIME_OK = 0,
    HIL_RUNTIME_NO_TRACK,
    HIL_RUNTIME_PARSE_ERROR,
    HIL_RUNTIME_DUPLICATE,
    HIL_RUNTIME_OUT_OF_ORDER,
    HIL_RUNTIME_MULTI_DET_UNSUPPORTED,
    HIL_RUNTIME_TIME_ERROR,
    HIL_RUNTIME_MEASUREMENT_ERROR,
    HIL_RUNTIME_TRACK_ERROR,
    HIL_RUNTIME_SERIALIZE_ERROR
} HilRuntimeResult;

uint32_t crc32c_compute(const uint8_t *data, size_t length);

HilParseResult hil_protocol_decode(
    const uint8_t *packet,
    size_t packet_len,
    HilFrameDecoded *out);

bool radar_measurement_from_hil(
    const HilFrameDecoded *frame,
    const HilDetectionDecoded *src,
    uint64_t receive_time_us,
    RadarMeasurement *out);

bool radar_measurement_to_cartesian(
    const RadarMeasurement *in,
    CartesianMeasurement *out);

void cv_tracker_reset(CvTrack *track);
bool cv_tracker_initialize(CvTrack *track, const CartesianMeasurement *m, uint32_t track_id);
bool cv_tracker_predict(CvTrack *track, uint64_t target_time_us);
bool cv_tracker_update(CvTrack *track, const CartesianMeasurement *m);
void cv_tracker_mark_miss(CvTrack *track);

bool track_state_from_cv(const CvTrack *src, TrackState *dst);

bool targetstate_build_v1(
    const TrackState *track,
    const RadarMeasurement *last_measurement,
    bool measurement_used_this_frame,
    bool reacquired_this_frame,
    uint64_t publish_time_us,
    TargetStateV1 *out);

bool targetstate_v1_serialize(
    const TargetStateV1 *state,
    uint32_t sequence,
    uint32_t source_id,
    uint32_t boot_id,
    uint8_t *dst,
    size_t capacity,
    size_t *written);

void hil_runtime_init(HilRuntime *rt, uint32_t source_id, uint32_t boot_id);

HilRuntimeResult hil_runtime_process_packet(
    HilRuntime *rt,
    const uint8_t *packet,
    size_t packet_len,
    uint64_t receive_time_us,
    uint64_t publish_time_us,
    uint8_t *response,
    size_t response_capacity,
    size_t *response_len);

#ifdef __cplusplus
}
#endif
