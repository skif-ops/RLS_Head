#include "rls/hil_r1.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define PI_F 3.14159265358979323846f
#define VALID_ALL 0x7Fu

#define CHECK(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return false; \
    } \
} while (0)

static bool nearf_abs(float actual, float expected, float tolerance)
{
    return fabsf(actual - expected) <= tolerance;
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

static uint32_t rd_u32_le(const uint8_t *p)
{
    return
        (uint32_t)p[0] |
        ((uint32_t)p[1] << 8) |
        ((uint32_t)p[2] << 16) |
        ((uint32_t)p[3] << 24);
}

static float rd_f32_le(const uint8_t *p)
{
    const uint32_t bits = rd_u32_le(p);
    float value;
    memcpy(&value, &bits, sizeof(value));
    return value;
}

static size_t make_frame(
    uint8_t *dst,
    size_t capacity,
    uint32_t sequence,
    uint32_t frame_id,
    uint64_t measurement_time_us,
    bool with_detection,
    float range_m,
    float range_variance)
{
    const uint16_t detection_count = with_detection ? 1u : 0u;
    const uint32_t payload_length =
        (uint32_t)detection_count * HIL_DETECTION_WIRE_SIZE;

    const size_t total =
        HIL_HEADER_WIRE_SIZE + payload_length + HIL_CRC_WIRE_SIZE;

    if (capacity < total) {
        return 0u;
    }

    uint8_t *p = dst;

    wr_u32_le(&p, HIL_PROTOCOL_MAGIC);
    wr_u16_le(&p, HIL_SCHEMA_MAJOR);
    wr_u16_le(&p, HIL_SCHEMA_MINOR);
    wr_u32_le(&p, sequence);
    wr_u32_le(&p, frame_id);
    wr_u64_le(&p, measurement_time_us);
    wr_u16_le(&p, detection_count);
    wr_u16_le(&p, 0u);
    wr_u32_le(&p, payload_length);

    if (with_detection) {
        wr_u32_le(&p, frame_id);

        wr_f32_le(&p, range_m);
        wr_f32_le(&p, 10.0f);
        wr_f32_le(&p, 0.0f);
        wr_f32_le(&p, 0.0f);

        float covariance[16] = {0};
        covariance[0] = range_variance;
        covariance[5] = 0.25f;
        covariance[10] = 1.0e-6f;
        covariance[15] = 1.0e-6f;

        for (unsigned i = 0; i < 16u; ++i) {
            wr_f32_le(&p, covariance[i]);
        }

        wr_f32_le(&p, 20.0f);
        wr_f32_le(&p, 1.0f);
        wr_f32_le(&p, 10.0f);

        wr_u32_le(&p, VALID_ALL);
        wr_u32_le(&p, 0x1234u);
    }

    const uint32_t crc = crc32c_compute(dst, total - HIL_CRC_WIRE_SIZE);
    wr_u32_le(&p, crc);

    return (size_t)(p - dst);
}

static bool process_frame(
    HilRuntime *runtime,
    uint32_t sequence,
    uint64_t measurement_time_us,
    bool with_detection,
    float range_m,
    float range_variance,
    uint64_t receive_time_us,
    uint64_t publish_time_us,
    uint8_t response[TARGETSTATE_PACKET_SIZE],
    HilRuntimeResult *result)
{
    uint8_t frame[HIL_HEADER_WIRE_SIZE + HIL_DETECTION_WIRE_SIZE + HIL_CRC_WIRE_SIZE];
    const size_t frame_len = make_frame(
        frame,
        sizeof(frame),
        sequence,
        sequence,
        measurement_time_us,
        with_detection,
        range_m,
        range_variance);

    CHECK(frame_len != 0u);

    size_t response_len = 0u;
    *result = hil_runtime_process_packet(
        runtime,
        frame,
        frame_len,
        receive_time_us,
        publish_time_us,
        response,
        TARGETSTATE_PACKET_SIZE,
        &response_len);

    if (*result == HIL_RUNTIME_OK) {
        CHECK(response_len == TARGETSTATE_PACKET_SIZE);
        CHECK(rd_u32_le(response) == TARGETSTATE_MAGIC);
        CHECK(crc32c_compute(response, 196u) == rd_u32_le(response + 196u));
    } else {
        CHECK(response_len == 0u);
    }

    return true;
}

static bool test_crc32c(void)
{
    static const uint8_t message[] = "123456789";
    CHECK(crc32c_compute(message, 9u) == 0xE3069283u);
    return true;
}

static bool test_r1_001_constant_velocity(void)
{
    HilRuntime rt;
    hil_runtime_init(&rt, 0x42u, 0x100u);

    uint8_t response[TARGETSTATE_PACKET_SIZE];
    HilRuntimeResult result;

    CHECK(process_frame(&rt, 1u, 1000000u, true, 100.0f, 0.0625f,
                        1000100u, 1000200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(rt.track.lifecycle == TRACK_TENTATIVE);
    CHECK(nearf_abs(rt.track.x[0], 100.0f, 1.0e-5f));

    CHECK(process_frame(&rt, 2u, 1050000u, true, 100.5f, 0.0625f,
                        1050100u, 1050200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(rt.track.lifecycle == TRACK_CONFIRMED);
    CHECK(nearf_abs(rt.track.x[0], 100.4166667f, 1.0e-4f));
    CHECK(nearf_abs(rt.track.x[3], 6.6666667f, 1.0e-4f));
    CHECK(nearf_abs(rt.track.P[0], 0.05208333f, 1.0e-5f));
    CHECK(nearf_abs(rt.track.P[3], 0.83333333f, 1.0e-5f));
    CHECK(nearf_abs(rt.track.P[21], 33.3333333f, 1.0e-4f));

    CHECK(process_frame(&rt, 3u, 1100000u, true, 101.0f, 0.0625f,
                        1100100u, 1100200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(nearf_abs(rt.track.x[0], 100.9444444f, 1.0e-4f));
    CHECK(nearf_abs(rt.track.x[3], 8.8888889f, 1.0e-4f));
    CHECK(nearf_abs(rt.track.P[0], 0.04861111f, 1.0e-5f));
    CHECK(nearf_abs(rt.track.P[3], 0.55555556f, 1.0e-5f));
    CHECK(nearf_abs(rt.track.P[21], 11.1111111f, 1.0e-4f));

    return true;
}

static bool test_r1_002_delay_semantics(void)
{
    HilRuntime rt;
    hil_runtime_init(&rt, 1u, 2u);

    uint8_t response[TARGETSTATE_PACKET_SIZE];
    HilRuntimeResult result;

    CHECK(process_frame(&rt, 1u, 1000000u, true, 100.0f, 0.0625f,
                        1020000u, 1021000u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);

    /* measurement_age_ms: header 24 + payload float index 16 at payload offset 36 */
    CHECK(nearf_abs(rd_f32_le(response + 124u), 21.0f, 1.0e-5f));

    return true;
}

static bool test_r1_003_dropout_reacquisition(void)
{
    HilRuntime rt;
    hil_runtime_init(&rt, 1u, 3u);

    uint8_t response[TARGETSTATE_PACKET_SIZE];
    HilRuntimeResult result;

    CHECK(process_frame(&rt, 1u, 1000000u, true, 100.0f, 0.0625f,
                        1000100u, 1000200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(process_frame(&rt, 2u, 1050000u, true, 100.5f, 0.0625f,
                        1050100u, 1050200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(process_frame(&rt, 3u, 1100000u, true, 101.0f, 0.0625f,
                        1100100u, 1100200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);

    CHECK(process_frame(&rt, 4u, 1150000u, false, 0.0f, 0.0f,
                        1150100u, 1150200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(rt.track.lifecycle == TRACK_COASTING);
    CHECK(nearf_abs(rt.track.x[0], 101.3888889f, 1.0e-4f));
    CHECK((rd_u32_le(response + 188u) & TS_FLAG_PREDICTED_STATE) != 0u);

    CHECK(process_frame(&rt, 5u, 1200000u, false, 0.0f, 0.0f,
                        1200100u, 1200200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(nearf_abs(rt.track.x[0], 101.8333333f, 1.0e-4f));

    CHECK(process_frame(&rt, 6u, 1250000u, false, 0.0f, 0.0f,
                        1250100u, 1250200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(nearf_abs(rt.track.x[0], 102.2777778f, 1.0e-4f));

    CHECK(process_frame(&rt, 7u, 1300000u, true, 103.0f, 0.0625f,
                        1300100u, 1300200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(rt.track.lifecycle == TRACK_CONFIRMED);
    CHECK(nearf_abs(rt.track.x[0], 102.9776786f, 1.0e-4f));
    CHECK(nearf_abs(rt.track.x[3], 9.8809524f, 1.0e-4f));
    CHECK(nearf_abs(rt.track.P[0], 0.05747768f, 1.0e-5f));
    CHECK(nearf_abs(rt.track.P[3], 0.22321429f, 1.0e-5f));
    CHECK(nearf_abs(rt.track.P[21], 1.1904762f, 1.0e-4f));
    CHECK((rd_u32_le(response + 188u) & TS_FLAG_REACQUIRED) != 0u);

    return true;
}

static bool test_r1_004_duplicate(void)
{
    HilRuntime rt;
    hil_runtime_init(&rt, 1u, 4u);

    uint8_t response[TARGETSTATE_PACKET_SIZE];
    HilRuntimeResult result;

    CHECK(process_frame(&rt, 10u, 1000000u, true, 100.0f, 0.0625f,
                        1000100u, 1000200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);

    const uint32_t updates_before = rt.diag.tracker_updates;
    const float x_before = rt.track.x[0];

    CHECK(process_frame(&rt, 10u, 1000000u, true, 100.0f, 0.0625f,
                        1000100u, 1000200u, response, &result));
    CHECK(result == HIL_RUNTIME_DUPLICATE);
    CHECK(rt.diag.duplicate_count == 1u);
    CHECK(rt.diag.tracker_updates == updates_before);
    CHECK(rt.track.x[0] == x_before);

    return true;
}

static bool test_r1_005_out_of_order(void)
{
    HilRuntime rt;
    hil_runtime_init(&rt, 1u, 5u);

    uint8_t response[TARGETSTATE_PACKET_SIZE];
    HilRuntimeResult result;

    CHECK(process_frame(&rt, 10u, 1000000u, true, 100.0f, 0.0625f,
                        1000100u, 1000200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);

    CHECK(process_frame(&rt, 12u, 1050000u, true, 100.5f, 0.0625f,
                        1050100u, 1050200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(rt.diag.frame_gap_count == 1u);

    CHECK(process_frame(&rt, 11u, 1100000u, true, 101.0f, 0.0625f,
                        1100100u, 1100200u, response, &result));
    CHECK(result == HIL_RUNTIME_OUT_OF_ORDER);
    CHECK(rt.diag.out_of_order_count == 1u);

    return true;
}

static bool test_r1_006_bad_crc(void)
{
    HilRuntime rt;
    hil_runtime_init(&rt, 1u, 6u);

    uint8_t frame[HIL_HEADER_WIRE_SIZE + HIL_DETECTION_WIRE_SIZE + HIL_CRC_WIRE_SIZE];
    const size_t len = make_frame(
        frame, sizeof(frame), 1u, 1u, 1000000u, true, 100.0f, 0.0625f);

    CHECK(len != 0u);
    frame[len - 1u] ^= 0x80u;

    uint8_t response[TARGETSTATE_PACKET_SIZE];
    size_t response_len = 0u;

    const HilRuntimeResult result = hil_runtime_process_packet(
        &rt, frame, len, 1000100u, 1000200u,
        response, sizeof(response), &response_len);

    CHECK(result == HIL_RUNTIME_PARSE_ERROR);
    CHECK(response_len == 0u);
    CHECK(rt.diag.crc_errors == 1u);
    CHECK(rt.diag.tracker_updates == 0u);

    return true;
}

static CartesianMeasurement cartesian_x(
    uint64_t time_us,
    float x,
    float var_x,
    float var_yz)
{
    CartesianMeasurement m;
    memset(&m, 0, sizeof(m));
    m.measurement_time_us = time_us;
    m.position_m[0] = x;
    m.covariance[0] = var_x;
    m.covariance[4] = var_yz;
    m.covariance[8] = var_yz;
    return m;
}

static bool test_r1_007_covariance_weighting(void)
{
    const CartesianMeasurement init =
        cartesian_x(1000000u, 100.0f, 0.0625f, 0.01f);

    CvTrack small;
    CvTrack large;

    CHECK(cv_tracker_initialize(&small, &init, 1u));
    CHECK(cv_tracker_initialize(&large, &init, 2u));

    CHECK(cv_tracker_predict(&small, 1050000u));
    CHECK(cv_tracker_predict(&large, 1050000u));

    const CartesianMeasurement z_small =
        cartesian_x(1050000u, 100.5f, 0.0625f, 0.01f);

    const CartesianMeasurement z_large =
        cartesian_x(1050000u, 100.5f, 4.0f, 1.0f);

    CHECK(cv_tracker_update(&small, &z_small));
    CHECK(cv_tracker_update(&large, &z_large));

    CHECK(fabsf(small.x[0] - 100.0f) > fabsf(large.x[0] - 100.0f));

    return true;
}

static RadarMeasurement polar_measurement(float range, float az, float el)
{
    RadarMeasurement m;
    memset(&m, 0, sizeof(m));
    m.measurement_time_us = 1u;
    m.range_m = range;
    m.azimuth_rad = az;
    m.elevation_rad = el;
    m.covariance[0] = 0.0625f;
    m.covariance[5] = 0.25f;
    m.covariance[10] = 1.0e-6f;
    m.covariance[15] = 1.0e-6f;
    return m;
}

static bool test_r1_008_coordinates(void)
{
    CartesianMeasurement c;

    RadarMeasurement m = polar_measurement(100.0f, 0.0f, 0.0f);
    CHECK(radar_measurement_to_cartesian(&m, &c));
    CHECK(nearf_abs(c.position_m[0], 100.0f, 1.0e-4f));
    CHECK(nearf_abs(c.position_m[1], 0.0f, 1.0e-4f));
    CHECK(nearf_abs(c.covariance[0], 0.0625f, 1.0e-5f));
    CHECK(nearf_abs(c.covariance[4], 0.0100f, 1.0e-5f));
    CHECK(nearf_abs(c.covariance[8], 0.0100f, 1.0e-5f));

    m = polar_measurement(100.0f, PI_F / 2.0f, 0.0f);
    CHECK(radar_measurement_to_cartesian(&m, &c));
    CHECK(nearf_abs(c.position_m[0], 0.0f, 1.0e-3f));
    CHECK(nearf_abs(c.position_m[1], 100.0f, 1.0e-3f));

    m = polar_measurement(100.0f, -PI_F / 2.0f, 0.0f);
    CHECK(radar_measurement_to_cartesian(&m, &c));
    CHECK(nearf_abs(c.position_m[1], -100.0f, 1.0e-3f));

    m = polar_measurement(100.0f, 0.0f, PI_F / 2.0f);
    CHECK(radar_measurement_to_cartesian(&m, &c));
    CHECK(nearf_abs(c.position_m[2], 100.0f, 1.0e-3f));

    m = polar_measurement(100.0f, PI_F / 4.0f, 0.0f);
    CHECK(radar_measurement_to_cartesian(&m, &c));
    CHECK(nearf_abs(c.position_m[0], 70.710678f, 1.0e-3f));
    CHECK(nearf_abs(c.position_m[1], 70.710678f, 1.0e-3f));

    return true;
}

static bool test_r1_009_long_replay(void)
{
    HilRuntime rt;
    hil_runtime_init(&rt, 1u, 9u);

    uint8_t response[TARGETSTATE_PACKET_SIZE];
    HilRuntimeResult result;

    for (uint32_t i = 0u; i < 10000u; ++i) {
        const uint64_t t = 1000000u + (uint64_t)i * 50000u;
        const float range = 100.0f + 10.0f * ((float)i * 0.05f);

        CHECK(process_frame(
            &rt,
            i + 1u,
            t,
            true,
            range,
            0.0625f,
            t + 100u,
            t + 200u,
            response,
            &result));

        CHECK(result == HIL_RUNTIME_OK);
        CHECK(isfinite(rt.track.x[0]));
        CHECK(isfinite(rt.track.x[3]));
    }

    CHECK(rt.diag.targetstate_tx == 10000u);
    CHECK(rt.diag.numeric_errors == 0u);

    return true;
}

static bool test_r1_010_reboot(void)
{
    HilRuntime first;
    hil_runtime_init(&first, 1u, 100u);

    uint8_t response[TARGETSTATE_PACKET_SIZE];
    HilRuntimeResult result;

    CHECK(process_frame(&first, 1u, 1000000u, true, 100.0f, 0.0625f,
                        1000100u, 1000200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(rd_u32_le(response + 20u) == 100u);

    HilRuntime second;
    hil_runtime_init(&second, 1u, 101u);

    CHECK(!second.have_track);

    CHECK(process_frame(&second, 1u, 2000000u, true, 200.0f, 0.0625f,
                        2000100u, 2000200u, response, &result));
    CHECK(result == HIL_RUNTIME_OK);
    CHECK(rd_u32_le(response + 20u) == 101u);
    CHECK(second.track.lifecycle == TRACK_TENTATIVE);
    CHECK(second.track.valid_updates == 1u);

    return true;
}

typedef bool (*TestFn)(void);

typedef struct {
    const char *name;
    TestFn fn;
} TestCase;

int main(void)
{
    const TestCase tests[] = {
        {"CRC32C", test_crc32c},
        {"R1-001 constant velocity", test_r1_001_constant_velocity},
        {"R1-002 delay semantics", test_r1_002_delay_semantics},
        {"R1-003 dropout/reacquisition", test_r1_003_dropout_reacquisition},
        {"R1-004 duplicate", test_r1_004_duplicate},
        {"R1-005 out-of-order", test_r1_005_out_of_order},
        {"R1-006 bad CRC", test_r1_006_bad_crc},
        {"R1-007 covariance weighting", test_r1_007_covariance_weighting},
        {"R1-008 coordinate transform", test_r1_008_coordinates},
        {"R1-009 long replay", test_r1_009_long_replay},
        {"R1-010 reboot", test_r1_010_reboot}
    };

    const size_t count = sizeof(tests) / sizeof(tests[0]);

    for (size_t i = 0; i < count; ++i) {
        if (!tests[i].fn()) {
            fprintf(stderr, "%s FAILED\n", tests[i].name);
            return 1;
        }

        printf("%s PASS\n", tests[i].name);
    }

    printf("HIL-R1 GOLDEN SUITE PASS (%zu tests)\n", count);
    return 0;
}
