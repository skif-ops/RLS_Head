#include "rls/hil_r1.h"

#include <math.h>
#include <string.h>

#define MAT3_DET_EPS 1.0e-12f
#define RAD_TO_DEG 57.29577951308232f
#define RANGE_EPS 1.0e-6f

enum {
    RADAR_VALID_RANGE      = 1u << 0,
    RADAR_VALID_RANGE_RATE = 1u << 1,
    RADAR_VALID_AZ         = 1u << 2,
    RADAR_VALID_EL         = 1u << 3,
    RADAR_VALID_COV        = 1u << 4,
    RADAR_VALID_TIME       = 1u << 5,
    RADAR_VALID_SNR        = 1u << 6
};

uint32_t crc32c_compute(const uint8_t *data, size_t length)
{
    uint32_t crc = 0xFFFFFFFFu;

    if (data == NULL && length != 0u) {
        return 0u;
    }

    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint32_t)data[i];

        for (unsigned bit = 0; bit < 8u; ++bit) {
            const uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
            crc = (crc >> 1) ^ (0x82F63B78u & mask);
        }
    }

    return ~crc;
}

static bool rd_u16_le(const uint8_t **p, const uint8_t *end, uint16_t *out)
{
    if (p == NULL || *p == NULL || out == NULL || end == NULL) {
        return false;
    }

    if ((size_t)(end - *p) < 2u) {
        return false;
    }

    const uint8_t *s = *p;
    *out = (uint16_t)s[0] | ((uint16_t)s[1] << 8);
    *p += 2;
    return true;
}

static bool rd_u32_le(const uint8_t **p, const uint8_t *end, uint32_t *out)
{
    if (p == NULL || *p == NULL || out == NULL || end == NULL) {
        return false;
    }

    if ((size_t)(end - *p) < 4u) {
        return false;
    }

    const uint8_t *s = *p;
    *out =
        (uint32_t)s[0] |
        ((uint32_t)s[1] << 8) |
        ((uint32_t)s[2] << 16) |
        ((uint32_t)s[3] << 24);

    *p += 4;
    return true;
}

static bool rd_u64_le(const uint8_t **p, const uint8_t *end, uint64_t *out)
{
    uint32_t lo;
    uint32_t hi;

    if (!rd_u32_le(p, end, &lo) || !rd_u32_le(p, end, &hi)) {
        return false;
    }

    *out = ((uint64_t)hi << 32) | (uint64_t)lo;
    return true;
}

static bool rd_f32_le(const uint8_t **p, const uint8_t *end, float *out)
{
    uint32_t bits;

    if (!rd_u32_le(p, end, &bits)) {
        return false;
    }

    memcpy(out, &bits, sizeof(bits));
    return isfinite(*out);
}

HilParseResult hil_protocol_decode(
    const uint8_t *packet,
    size_t packet_len,
    HilFrameDecoded *out)
{
    if (packet == NULL || out == NULL) {
        return HIL_PARSE_BAD_LENGTH;
    }

    if (packet_len < HIL_HEADER_WIRE_SIZE + HIL_CRC_WIRE_SIZE) {
        return HIL_PARSE_BAD_LENGTH;
    }

    const uint8_t *p = packet;
    const uint8_t *crc_pos = packet + packet_len - HIL_CRC_WIRE_SIZE;

    uint32_t magic;
    uint16_t major;
    uint16_t minor;
    uint32_t sequence;
    uint32_t frame_id;
    uint64_t measurement_time_us;
    uint16_t detection_count;
    uint16_t flags;
    uint32_t payload_length;

    if (!rd_u32_le(&p, crc_pos, &magic) ||
        !rd_u16_le(&p, crc_pos, &major) ||
        !rd_u16_le(&p, crc_pos, &minor) ||
        !rd_u32_le(&p, crc_pos, &sequence) ||
        !rd_u32_le(&p, crc_pos, &frame_id) ||
        !rd_u64_le(&p, crc_pos, &measurement_time_us) ||
        !rd_u16_le(&p, crc_pos, &detection_count) ||
        !rd_u16_le(&p, crc_pos, &flags) ||
        !rd_u32_le(&p, crc_pos, &payload_length)) {
        return HIL_PARSE_TRUNCATED;
    }

    if (magic != HIL_PROTOCOL_MAGIC) {
        return HIL_PARSE_BAD_MAGIC;
    }

    if (major != HIL_SCHEMA_MAJOR || minor != HIL_SCHEMA_MINOR) {
        return HIL_PARSE_BAD_VERSION;
    }

    if (detection_count > HIL_MAX_DETECTIONS) {
        return HIL_PARSE_TOO_MANY_DETECTIONS;
    }

    const size_t expected_payload =
        (size_t)detection_count * HIL_DETECTION_WIRE_SIZE;

    if ((size_t)payload_length != expected_payload) {
        return HIL_PARSE_BAD_LENGTH;
    }

    const size_t expected_packet =
        HIL_HEADER_WIRE_SIZE + expected_payload + HIL_CRC_WIRE_SIZE;

    if (packet_len != expected_packet) {
        return HIL_PARSE_BAD_LENGTH;
    }

    uint32_t crc_wire;
    const uint8_t *crc_reader = crc_pos;

    if (!rd_u32_le(&crc_reader, packet + packet_len, &crc_wire)) {
        return HIL_PARSE_TRUNCATED;
    }

    const uint32_t crc_calc =
        crc32c_compute(packet, packet_len - HIL_CRC_WIRE_SIZE);

    if (crc_calc != crc_wire) {
        return HIL_PARSE_BAD_CRC;
    }

    memset(out, 0, sizeof(*out));
    out->sequence = sequence;
    out->frame_id = frame_id;
    out->measurement_time_us = measurement_time_us;
    out->detection_count = detection_count;
    out->flags = flags;

    for (uint16_t i = 0; i < detection_count; ++i) {
        HilDetectionDecoded *d = &out->detections[i];

        if (!rd_u32_le(&p, crc_pos, &d->detection_id)) {
            return HIL_PARSE_TRUNCATED;
        }

        if (!rd_f32_le(&p, crc_pos, &d->range_m) ||
            !rd_f32_le(&p, crc_pos, &d->range_rate_m_s) ||
            !rd_f32_le(&p, crc_pos, &d->azimuth_rad) ||
            !rd_f32_le(&p, crc_pos, &d->elevation_rad)) {
            return HIL_PARSE_INVALID_FLOAT;
        }

        for (unsigned k = 0; k < 16u; ++k) {
            if (!rd_f32_le(&p, crc_pos, &d->covariance[k])) {
                return HIL_PARSE_INVALID_FLOAT;
            }
        }

        if (!rd_f32_le(&p, crc_pos, &d->snr_db) ||
            !rd_f32_le(&p, crc_pos, &d->quality) ||
            !rd_f32_le(&p, crc_pos, &d->timestamp_uncertainty_us)) {
            return HIL_PARSE_INVALID_FLOAT;
        }

        if (!rd_u32_le(&p, crc_pos, &d->validity_flags) ||
            !rd_u32_le(&p, crc_pos, &d->radar_flags)) {
            return HIL_PARSE_TRUNCATED;
        }
    }

    if (p != crc_pos) {
        return HIL_PARSE_BAD_LENGTH;
    }

    return HIL_PARSE_OK;
}

bool radar_measurement_from_hil(
    const HilFrameDecoded *frame,
    const HilDetectionDecoded *src,
    uint64_t receive_time_us,
    RadarMeasurement *out)
{
    if (frame == NULL || src == NULL || out == NULL) {
        return false;
    }

    const uint32_t mandatory =
        RADAR_VALID_RANGE |
        RADAR_VALID_AZ |
        RADAR_VALID_EL |
        RADAR_VALID_COV |
        RADAR_VALID_TIME;

    if ((src->validity_flags & mandatory) != mandatory) {
        return false;
    }

    if (!isfinite(src->range_m) ||
        !isfinite(src->range_rate_m_s) ||
        !isfinite(src->azimuth_rad) ||
        !isfinite(src->elevation_rad) ||
        !isfinite(src->snr_db) ||
        !isfinite(src->quality) ||
        !isfinite(src->timestamp_uncertainty_us)) {
        return false;
    }

    if (src->range_m < 0.0f || frame->measurement_time_us == 0u) {
        return false;
    }

    for (unsigned i = 0; i < 16u; ++i) {
        if (!isfinite(src->covariance[i])) {
            return false;
        }
    }

    for (unsigned i = 0; i < 4u; ++i) {
        if (src->covariance[i * 4u + i] < 0.0f) {
            return false;
        }
    }

    memset(out, 0, sizeof(*out));
    out->measurement_time_us = frame->measurement_time_us;
    out->receive_time_us = receive_time_us;
    out->frame_id = frame->frame_id;
    out->detection_id = src->detection_id;
    out->range_m = src->range_m;
    out->range_rate_m_s = src->range_rate_m_s;
    out->azimuth_rad = src->azimuth_rad;
    out->elevation_rad = src->elevation_rad;
    memcpy(out->covariance, src->covariance, sizeof(out->covariance));
    out->snr_db = src->snr_db;
    out->quality = src->quality;
    out->timestamp_uncertainty_us = src->timestamp_uncertainty_us;
    out->validity_flags = src->validity_flags;
    out->radar_flags = src->radar_flags;

    return true;
}

static bool matrix_finite(const float *m, unsigned count)
{
    if (m == NULL) {
        return false;
    }

    for (unsigned i = 0; i < count; ++i) {
        if (!isfinite(m[i])) {
            return false;
        }
    }

    return true;
}

bool radar_measurement_to_cartesian(
    const RadarMeasurement *in,
    CartesianMeasurement *out)
{
    if (in == NULL || out == NULL) {
        return false;
    }

    const float range = in->range_m;
    const float az = in->azimuth_rad;
    const float el = in->elevation_rad;

    if (!isfinite(range) || !isfinite(az) || !isfinite(el) || range < 0.0f) {
        return false;
    }

    const float ca = cosf(az);
    const float sa = sinf(az);
    const float ce = cosf(el);
    const float se = sinf(el);

    memset(out, 0, sizeof(*out));

    out->measurement_time_us = in->measurement_time_us;
    out->position_m[0] = range * ce * ca;
    out->position_m[1] = range * ce * sa;
    out->position_m[2] = range * se;

    const float jacobian[9] = {
        ce * ca, -range * ce * sa, -range * se * ca,
        ce * sa,  range * ce * ca, -range * se * sa,
        se,       0.0f,             range * ce
    };

    static const unsigned idx[3] = {0u, 2u, 3u};
    float q[9];

    for (unsigned r = 0; r < 3u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            q[r * 3u + c] = in->covariance[idx[r] * 4u + idx[c]];
        }
    }

    float tmp[9] = {0};
    float pxyz[9] = {0};

    for (unsigned r = 0; r < 3u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            for (unsigned k = 0; k < 3u; ++k) {
                tmp[r * 3u + c] +=
                    jacobian[r * 3u + k] * q[k * 3u + c];
            }
        }
    }

    for (unsigned r = 0; r < 3u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            for (unsigned k = 0; k < 3u; ++k) {
                pxyz[r * 3u + c] +=
                    tmp[r * 3u + k] * jacobian[c * 3u + k];
            }
        }
    }

    if (!matrix_finite(pxyz, 9u)) {
        return false;
    }

    for (unsigned i = 0; i < 3u; ++i) {
        if (pxyz[i * 3u + i] < -1.0e-6f) {
            return false;
        }
    }

    memcpy(out->covariance, pxyz, sizeof(pxyz));
    out->range_rate_m_s = in->range_rate_m_s;

    const float vr_var = in->covariance[5u];
    if (!isfinite(vr_var) || vr_var < 0.0f) {
        return false;
    }

    out->range_rate_sigma_m_s = sqrtf(vr_var);
    out->quality = in->quality;
    out->flags = in->validity_flags;

    return true;
}

static bool mat3_inverse(const float a[9], float inv[9])
{
    const float m00 = a[0];
    const float m01 = a[1];
    const float m02 = a[2];
    const float m10 = a[3];
    const float m11 = a[4];
    const float m12 = a[5];
    const float m20 = a[6];
    const float m21 = a[7];
    const float m22 = a[8];

    const float c00 = m11 * m22 - m12 * m21;
    const float c01 = m02 * m21 - m01 * m22;
    const float c02 = m01 * m12 - m02 * m11;
    const float c10 = m12 * m20 - m10 * m22;
    const float c11 = m00 * m22 - m02 * m20;
    const float c12 = m02 * m10 - m00 * m12;
    const float c20 = m10 * m21 - m11 * m20;
    const float c21 = m01 * m20 - m00 * m21;
    const float c22 = m00 * m11 - m01 * m10;

    const float det = m00 * c00 + m01 * c10 + m02 * c20;

    if (!isfinite(det) || fabsf(det) < MAT3_DET_EPS) {
        return false;
    }

    const float scale = 1.0f / det;

    inv[0] = c00 * scale;
    inv[1] = c01 * scale;
    inv[2] = c02 * scale;
    inv[3] = c10 * scale;
    inv[4] = c11 * scale;
    inv[5] = c12 * scale;
    inv[6] = c20 * scale;
    inv[7] = c21 * scale;
    inv[8] = c22 * scale;

    return matrix_finite(inv, 9u);
}

static void symmetrize6(float p[36])
{
    for (unsigned r = 0; r < 6u; ++r) {
        for (unsigned c = r + 1u; c < 6u; ++c) {
            const float v = 0.5f * (p[r * 6u + c] + p[c * 6u + r]);
            p[r * 6u + c] = v;
            p[c * 6u + r] = v;
        }
    }
}

static bool covariance_valid6(const float p[36])
{
    if (!matrix_finite(p, 36u)) {
        return false;
    }

    for (unsigned i = 0; i < 6u; ++i) {
        if (p[i * 6u + i] < -1.0e-5f) {
            return false;
        }
    }

    return true;
}

void cv_tracker_reset(CvTrack *track)
{
    if (track != NULL) {
        memset(track, 0, sizeof(*track));
    }
}

bool cv_tracker_initialize(
    CvTrack *track,
    const CartesianMeasurement *m,
    uint32_t track_id)
{
    if (track == NULL || m == NULL) {
        return false;
    }

    if (!matrix_finite(m->position_m, 3u) ||
        !matrix_finite(m->covariance, 9u)) {
        return false;
    }

    cv_tracker_reset(track);

    track->x[0] = m->position_m[0];
    track->x[1] = m->position_m[1];
    track->x[2] = m->position_m[2];

    for (unsigned r = 0; r < 3u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            track->P[r * 6u + c] = m->covariance[r * 3u + c];
        }
    }

    track->P[21u] = 100.0f;
    track->P[28u] = 100.0f;
    track->P[35u] = 100.0f;

    track->state_time_us = m->measurement_time_us;
    track->last_measurement_time_us = m->measurement_time_us;
    track->track_id = track_id;
    track->lifecycle = TRACK_TENTATIVE;
    track->valid_updates = 1u;

    return covariance_valid6(track->P);
}

bool cv_tracker_predict(CvTrack *track, uint64_t target_time_us)
{
    if (track == NULL || track->lifecycle == TRACK_NONE) {
        return false;
    }

    if (target_time_us < track->state_time_us) {
        return false;
    }

    const float dt =
        (float)(target_time_us - track->state_time_us) * 1.0e-6f;

    if (!isfinite(dt)) {
        return false;
    }

    track->x[0] += track->x[3] * dt;
    track->x[1] += track->x[4] * dt;
    track->x[2] += track->x[5] * dt;

    float f[36] = {0};
    for (unsigned i = 0; i < 6u; ++i) {
        f[i * 6u + i] = 1.0f;
    }

    f[3u] = dt;
    f[10u] = dt;
    f[17u] = dt;

    float tmp[36] = {0};
    float pnew[36] = {0};

    for (unsigned r = 0; r < 6u; ++r) {
        for (unsigned c = 0; c < 6u; ++c) {
            for (unsigned k = 0; k < 6u; ++k) {
                tmp[r * 6u + c] +=
                    f[r * 6u + k] * track->P[k * 6u + c];
            }
        }
    }

    for (unsigned r = 0; r < 6u; ++r) {
        for (unsigned c = 0; c < 6u; ++c) {
            for (unsigned k = 0; k < 6u; ++k) {
                pnew[r * 6u + c] +=
                    tmp[r * 6u + k] * f[c * 6u + k];
            }
        }
    }

    memcpy(track->P, pnew, sizeof(pnew));
    symmetrize6(track->P);

    if (!covariance_valid6(track->P) || !matrix_finite(track->x, 6u)) {
        return false;
    }

    track->state_time_us = target_time_us;
    return true;
}

bool cv_tracker_update(CvTrack *track, const CartesianMeasurement *m)
{
    if (track == NULL || m == NULL || track->lifecycle == TRACK_NONE) {
        return false;
    }

    if (m->measurement_time_us != track->state_time_us) {
        return false;
    }

    float innovation[3] = {
        m->position_m[0] - track->x[0],
        m->position_m[1] - track->x[1],
        m->position_m[2] - track->x[2]
    };

    float s[9];
    for (unsigned r = 0; r < 3u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            s[r * 3u + c] =
                track->P[r * 6u + c] + m->covariance[r * 3u + c];
        }
    }

    float s_inv[9];
    if (!mat3_inverse(s, s_inv)) {
        return false;
    }

    float k_gain[18] = {0};

    for (unsigned r = 0; r < 6u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            for (unsigned j = 0; j < 3u; ++j) {
                k_gain[r * 3u + c] +=
                    track->P[r * 6u + j] * s_inv[j * 3u + c];
            }
        }
    }

    for (unsigned r = 0; r < 6u; ++r) {
        float correction = 0.0f;
        for (unsigned j = 0; j < 3u; ++j) {
            correction += k_gain[r * 3u + j] * innovation[j];
        }
        track->x[r] += correction;
    }

    float a[36] = {0};
    for (unsigned i = 0; i < 6u; ++i) {
        a[i * 6u + i] = 1.0f;
    }

    for (unsigned r = 0; r < 6u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            a[r * 6u + c] -= k_gain[r * 3u + c];
        }
    }

    float ap[36] = {0};
    float apat[36] = {0};

    for (unsigned r = 0; r < 6u; ++r) {
        for (unsigned c = 0; c < 6u; ++c) {
            for (unsigned j = 0; j < 6u; ++j) {
                ap[r * 6u + c] += a[r * 6u + j] * track->P[j * 6u + c];
            }
        }
    }

    for (unsigned r = 0; r < 6u; ++r) {
        for (unsigned c = 0; c < 6u; ++c) {
            for (unsigned j = 0; j < 6u; ++j) {
                apat[r * 6u + c] += ap[r * 6u + j] * a[c * 6u + j];
            }
        }
    }

    float kr[18] = {0};
    float krkt[36] = {0};

    for (unsigned r = 0; r < 6u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            for (unsigned j = 0; j < 3u; ++j) {
                kr[r * 3u + c] +=
                    k_gain[r * 3u + j] * m->covariance[j * 3u + c];
            }
        }
    }

    for (unsigned r = 0; r < 6u; ++r) {
        for (unsigned c = 0; c < 6u; ++c) {
            for (unsigned j = 0; j < 3u; ++j) {
                krkt[r * 6u + c] +=
                    kr[r * 3u + j] * k_gain[c * 3u + j];
            }
        }
    }

    for (unsigned i = 0; i < 36u; ++i) {
        track->P[i] = apat[i] + krkt[i];
    }

    symmetrize6(track->P);

    if (!covariance_valid6(track->P) || !matrix_finite(track->x, 6u)) {
        return false;
    }

    track->last_measurement_time_us = m->measurement_time_us;
    track->consecutive_misses = 0u;
    ++track->valid_updates;

    if (track->valid_updates >= 2u) {
        track->lifecycle = TRACK_CONFIRMED;
    }

    return true;
}

void cv_tracker_mark_miss(CvTrack *track)
{
    if (track == NULL || track->lifecycle == TRACK_NONE) {
        return;
    }

    ++track->consecutive_misses;

    if (track->lifecycle == TRACK_CONFIRMED) {
        track->lifecycle = TRACK_COASTING;
    }
}

bool track_state_from_cv(const CvTrack *src, TrackState *dst)
{
    if (src == NULL || dst == NULL || src->lifecycle == TRACK_NONE) {
        return false;
    }

    memset(dst, 0, sizeof(*dst));
    dst->track_id = src->track_id;
    dst->state_time_us = src->state_time_us;
    dst->last_measurement_time_us = src->last_measurement_time_us;

    for (unsigned i = 0; i < 3u; ++i) {
        dst->position_m[i] = src->x[i];
        dst->velocity_m_s[i] = src->x[i + 3u];

        if (!isfinite(dst->position_m[i]) || !isfinite(dst->velocity_m_s[i])) {
            return false;
        }
    }

    for (unsigned r = 0; r < 3u; ++r) {
        for (unsigned c = 0; c < 3u; ++c) {
            dst->position_cov[r * 3u + c] = src->P[r * 6u + c];
            dst->velocity_cov[r * 3u + c] =
                src->P[(r + 3u) * 6u + (c + 3u)];
        }
    }

    dst->lifecycle = (uint32_t)src->lifecycle;
    return true;
}

static void mat3_to_ut6(const float p[9], float out[6])
{
    out[0] = p[0];
    out[1] = p[1];
    out[2] = p[2];
    out[3] = p[4];
    out[4] = p[5];
    out[5] = p[8];
}

bool targetstate_build_v1(
    const TrackState *track,
    const RadarMeasurement *last_measurement,
    bool measurement_used_this_frame,
    bool reacquired_this_frame,
    uint64_t publish_time_us,
    TargetStateV1 *out)
{
    if (track == NULL || last_measurement == NULL || out == NULL) {
        return false;
    }

    if (publish_time_us < track->last_measurement_time_us) {
        return false;
    }

    memset(out, 0, sizeof(*out));

    out->measurement_timestamp_us = track->last_measurement_time_us;
    out->state_timestamp_us = track->state_time_us;
    out->publish_timestamp_us = publish_time_us;
    out->track_id = track->track_id;
    out->coordinate_frame = TS_FRAME_BODY_FRU;
    out->track_state = (uint8_t)track->lifecycle;
    out->motion_model = TS_MOTION_CV;

    out->validity_mask =
        TS_VALID_RANGE |
        TS_VALID_RANGE_RATE |
        TS_VALID_ANGLES |
        TS_VALID_POSITION |
        TS_VALID_VELOCITY |
        TS_VALID_POS_COV |
        TS_VALID_VEL_COV |
        TS_VALID_SNR |
        TS_VALID_TIME;

    for (unsigned i = 0; i < 3u; ++i) {
        out->relative_position_m[i] = track->position_m[i];
        out->relative_velocity_m_s[i] = track->velocity_m_s[i];
        out->relative_accel_m_s2[i] = 0.0f;
    }

    const float x = track->position_m[0];
    const float y = track->position_m[1];
    const float z = track->position_m[2];
    const float vx = track->velocity_m_s[0];
    const float vy = track->velocity_m_s[1];
    const float vz = track->velocity_m_s[2];

    const float horizontal = sqrtf(x * x + y * y);
    const float range = sqrtf(x * x + y * y + z * z);

    out->range_m = range;
    out->azimuth_deg = atan2f(y, x) * RAD_TO_DEG;
    out->elevation_deg = atan2f(z, horizontal) * RAD_TO_DEG;

    if (range > RANGE_EPS) {
        out->range_rate_m_s = (x * vx + y * vy + z * vz) / range;
    }

    out->snr_db = last_measurement->snr_db;
    out->measurement_age_ms =
        (float)(publish_time_us - track->last_measurement_time_us) * 0.001f;

    mat3_to_ut6(track->position_cov, out->position_cov_ut);
    mat3_to_ut6(track->velocity_cov, out->velocity_cov_ut);

    out->timestamp_uncertainty_us =
        last_measurement->timestamp_uncertainty_us;

    out->radar_status = last_measurement->radar_flags;
    out->fusion_status = 0u;

    out->track_flags = TS_FLAG_TIME_VALID | TS_FLAG_COV_VALID;

    if (measurement_used_this_frame) {
        out->track_flags |= TS_FLAG_MEASUREMENT_VALID;
    } else {
        out->track_flags |= TS_FLAG_PREDICTED_STATE;
    }

    if (reacquired_this_frame) {
        out->track_flags |= TS_FLAG_REACQUIRED;
    }

    if ((out->track_flags & TS_FLAG_MEASUREMENT_VALID) != 0u &&
        (out->track_flags & TS_FLAG_PREDICTED_STATE) != 0u) {
        return false;
    }

    return true;
}

static void wr_u8(uint8_t **p, uint8_t value)
{
    *(*p)++ = value;
}

static void wr_u16_le(uint8_t **p, uint16_t value)
{
    *(*p)++ = (uint8_t)value;
    *(*p)++ = (uint8_t)(value >> 8);
}

static void wr_u32_le(uint8_t **p, uint32_t value)
{
    *(*p)++ = (uint8_t)value;
    *(*p)++ = (uint8_t)(value >> 8);
    *(*p)++ = (uint8_t)(value >> 16);
    *(*p)++ = (uint8_t)(value >> 24);
}

static void wr_u64_le(uint8_t **p, uint64_t value)
{
    wr_u32_le(p, (uint32_t)(value & 0xFFFFFFFFu));
    wr_u32_le(p, (uint32_t)(value >> 32));
}

static void wr_f32_le(uint8_t **p, float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof(bits));
    wr_u32_le(p, bits);
}

bool targetstate_v1_serialize(
    const TargetStateV1 *state,
    uint32_t sequence,
    uint32_t source_id,
    uint32_t boot_id,
    uint8_t *dst,
    size_t capacity,
    size_t *written)
{
    if (state == NULL || dst == NULL || written == NULL) {
        return false;
    }

    if (capacity < TARGETSTATE_PACKET_SIZE) {
        return false;
    }

    uint8_t *p = dst;

    wr_u32_le(&p, TARGETSTATE_MAGIC);
    wr_u8(&p, TARGETSTATE_MAJOR);
    wr_u8(&p, TARGETSTATE_MINOR);
    wr_u8(&p, TARGETSTATE_MSG_STATE);
    wr_u8(&p, 0u);
    wr_u16_le(&p, TARGETSTATE_PAYLOAD_SIZE);
    wr_u16_le(&p, TARGETSTATE_HEADER_SIZE);
    wr_u32_le(&p, sequence);
    wr_u32_le(&p, source_id);
    wr_u32_le(&p, boot_id);

    wr_u64_le(&p, state->measurement_timestamp_us);
    wr_u64_le(&p, state->state_timestamp_us);
    wr_u64_le(&p, state->publish_timestamp_us);
    wr_u32_le(&p, state->track_id);

    wr_u8(&p, state->coordinate_frame);
    wr_u8(&p, state->track_state);
    wr_u8(&p, state->motion_model);
    wr_u8(&p, state->reserved0);

    wr_u32_le(&p, state->validity_mask);

    wr_f32_le(&p, state->range_m);
    wr_f32_le(&p, state->range_rate_m_s);
    wr_f32_le(&p, state->azimuth_deg);
    wr_f32_le(&p, state->elevation_deg);

    for (unsigned i = 0; i < 3u; ++i) {
        wr_f32_le(&p, state->relative_position_m[i]);
    }

    for (unsigned i = 0; i < 3u; ++i) {
        wr_f32_le(&p, state->relative_velocity_m_s[i]);
    }

    for (unsigned i = 0; i < 3u; ++i) {
        wr_f32_le(&p, state->relative_accel_m_s2[i]);
    }

    wr_f32_le(&p, state->snr_db);
    wr_f32_le(&p, state->track_quality);
    wr_f32_le(&p, state->confidence);
    wr_f32_le(&p, state->measurement_age_ms);

    for (unsigned i = 0; i < 6u; ++i) {
        wr_f32_le(&p, state->position_cov_ut[i]);
    }

    for (unsigned i = 0; i < 6u; ++i) {
        wr_f32_le(&p, state->velocity_cov_ut[i]);
    }

    wr_f32_le(&p, state->timestamp_uncertainty_us);
    wr_u32_le(&p, state->radar_status);
    wr_u32_le(&p, state->fusion_status);
    wr_u32_le(&p, state->track_flags);
    wr_u32_le(&p, state->reserved1);

    if ((size_t)(p - dst) !=
        TARGETSTATE_PACKET_SIZE - TARGETSTATE_CRC_SIZE) {
        return false;
    }

    const uint32_t crc =
        crc32c_compute(dst, TARGETSTATE_PACKET_SIZE - TARGETSTATE_CRC_SIZE);

    wr_u32_le(&p, crc);

    if ((size_t)(p - dst) != TARGETSTATE_PACKET_SIZE) {
        return false;
    }

    *written = TARGETSTATE_PACKET_SIZE;
    return true;
}

void hil_runtime_init(HilRuntime *rt, uint32_t source_id, uint32_t boot_id)
{
    if (rt == NULL) {
        return;
    }

    memset(rt, 0, sizeof(*rt));
    rt->source_id = source_id;
    rt->boot_id = boot_id;
    rt->next_track_id = 1u;
    rt->targetstate_sequence = 1u;
}

static int32_t sequence_delta(uint32_t newer, uint32_t older)
{
    return (int32_t)(newer - older);
}

HilRuntimeResult hil_runtime_process_packet(
    HilRuntime *rt,
    const uint8_t *packet,
    size_t packet_len,
    uint64_t receive_time_us,
    uint64_t publish_time_us,
    uint8_t *response,
    size_t response_capacity,
    size_t *response_len)
{
    if (rt == NULL || packet == NULL || response == NULL || response_len == NULL) {
        return HIL_RUNTIME_PARSE_ERROR;
    }

    *response_len = 0u;
    ++rt->diag.frames_rx;

    HilFrameDecoded frame;
    const HilParseResult parse_result =
        hil_protocol_decode(packet, packet_len, &frame);

    if (parse_result != HIL_PARSE_OK) {
        if (parse_result == HIL_PARSE_BAD_CRC) {
            ++rt->diag.crc_errors;
        }

        return HIL_RUNTIME_PARSE_ERROR;
    }

    ++rt->diag.frames_valid;

    if (rt->have_sequence) {
        const int32_t delta = sequence_delta(frame.sequence, rt->last_sequence);

        if (delta == 0) {
            ++rt->diag.duplicate_count;
            return HIL_RUNTIME_DUPLICATE;
        }

        if (delta < 0) {
            ++rt->diag.out_of_order_count;
            return HIL_RUNTIME_OUT_OF_ORDER;
        }

        if (delta > 1) {
            rt->diag.frame_gap_count += (uint32_t)(delta - 1);
        }
    }

    rt->last_sequence = frame.sequence;
    rt->have_sequence = true;

    if (frame.detection_count > 1u) {
        return HIL_RUNTIME_MULTI_DET_UNSUPPORTED;
    }

    bool measurement_used = false;
    bool reacquired = false;

    if (frame.detection_count == 1u) {
        RadarMeasurement measurement;

        if (!radar_measurement_from_hil(
                &frame,
                &frame.detections[0],
                receive_time_us,
                &measurement)) {
            ++rt->diag.numeric_errors;
            return HIL_RUNTIME_MEASUREMENT_ERROR;
        }

        CartesianMeasurement cartesian;

        if (!radar_measurement_to_cartesian(&measurement, &cartesian)) {
            ++rt->diag.numeric_errors;
            return HIL_RUNTIME_MEASUREMENT_ERROR;
        }

        if (!rt->have_track) {
            if (!cv_tracker_initialize(
                    &rt->track,
                    &cartesian,
                    rt->next_track_id++)) {
                return HIL_RUNTIME_TRACK_ERROR;
            }

            rt->have_track = true;
        } else {
            if (cartesian.measurement_time_us < rt->track.state_time_us) {
                return HIL_RUNTIME_TIME_ERROR;
            }

            const TrackLifecycle before = rt->track.lifecycle;

            if (!cv_tracker_predict(
                    &rt->track,
                    cartesian.measurement_time_us)) {
                return HIL_RUNTIME_TRACK_ERROR;
            }

            if (!cv_tracker_update(&rt->track, &cartesian)) {
                return HIL_RUNTIME_TRACK_ERROR;
            }

            reacquired = before == TRACK_COASTING;
        }

        rt->last_measurement = measurement;
        rt->have_last_measurement = true;
        measurement_used = true;
        ++rt->diag.tracker_updates;
    } else {
        if (!rt->have_track) {
            return HIL_RUNTIME_NO_TRACK;
        }

        if (frame.measurement_time_us < rt->track.state_time_us) {
            return HIL_RUNTIME_TIME_ERROR;
        }

        if (!cv_tracker_predict(&rt->track, frame.measurement_time_us)) {
            return HIL_RUNTIME_TRACK_ERROR;
        }

        cv_tracker_mark_miss(&rt->track);
        ++rt->diag.tracker_misses;
    }

    if (!rt->have_last_measurement) {
        return HIL_RUNTIME_NO_TRACK;
    }

    TrackState track_state;

    if (!track_state_from_cv(&rt->track, &track_state)) {
        return HIL_RUNTIME_TRACK_ERROR;
    }

    TargetStateV1 target_state;

    if (!targetstate_build_v1(
            &track_state,
            &rt->last_measurement,
            measurement_used,
            reacquired,
            publish_time_us,
            &target_state)) {
        return HIL_RUNTIME_TIME_ERROR;
    }

    if (!targetstate_v1_serialize(
            &target_state,
            rt->targetstate_sequence++,
            rt->source_id,
            rt->boot_id,
            response,
            response_capacity,
            response_len)) {
        return HIL_RUNTIME_SERIALIZE_ERROR;
    }

    ++rt->diag.targetstate_tx;
    return HIL_RUNTIME_OK;
}
