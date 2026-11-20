#include "rls/awr2944p_observer.h"

#include <stdint.h>
#include <string.h>

#define CHECK(condition) do { if (!(condition)) return __LINE__; } while (0)

static int start_observer(rls_awr2944p_observer_t *observer)
{
    rls_awr2944p_observer_config_t config;
    rls_awr2944p_observer_default_config(&config);
    return rls_awr2944p_observer_init(observer, &config, 0x10203040u, 1u);
}

static int test_polar_measurement_and_confirmation(void)
{
    rls_awr2944p_observer_t observer;
    rls_awr2944p_observer_output_t output;
    const rls_awr2944p_detection_t detection = {
        .x_m = 3.0f,
        .y_m = 4.0f,
        .z_m = 0.0f,
        .radial_velocity_m_s = -10.0f,
        .snr_decidb = 150,
        .noise_decidb = 40,
    };
    CHECK(start_observer(&observer) == 0);

    CHECK(rls_awr2944p_observer_process(
        &observer, &detection, 1u, 1000u, &output) == 0);
    CHECK(output.fresh_detection);
    CHECK(output.measurement.target_id == 1u);
    CHECK(output.measurement.range_mm == 5000u);
    CHECK(output.measurement.radial_velocity_mm_s == -10000);
    CHECK(output.measurement.azimuth_mdeg >= 36869);
    CHECK(output.measurement.azimuth_mdeg <= 36871);
    CHECK(output.measurement.elevation_mdeg == 0);
    CHECK(output.measurement.snr_cdb == 1500);
    CHECK(output.measurement.rcs_cdbsm == 0);
    CHECK((output.measurement.quality_flags & RLS_RADAR_QUALITY_RCS_VALID) == 0u);
    CHECK((output.measurement.quality_flags
        & RLS_RADAR_QUALITY_UNCERTAINTY_VALID) == 0u);
    CHECK(output.measurement.track_state == RLS_RADAR_TRACK_TENTATIVE);
    CHECK((output.status_flags & RLS_RADAR_STATUS_CONFIG_MATCH) == 0u);

    CHECK(rls_awr2944p_observer_process(
        &observer, &detection, 1u, 2000u, &output) == 0);
    CHECK(output.measurement.track_state == RLS_RADAR_TRACK_TENTATIVE);
    CHECK(rls_awr2944p_observer_process(
        &observer, &detection, 1u, 3000u, &output) == 0);
    CHECK(output.measurement.track_state == RLS_RADAR_TRACK_CONFIRMED);
    CHECK((output.measurement.quality_flags
        & RLS_RADAR_QUALITY_TRACK_CONFIRMED) != 0u);
    return 0;
}

static int test_coast_loss_and_reacquisition(void)
{
    rls_awr2944p_observer_t observer;
    rls_awr2944p_observer_output_t output;
    const rls_awr2944p_detection_t detection = {
        .x_m = 0.0f,
        .y_m = 100.0f,
        .z_m = 0.0f,
        .radial_velocity_m_s = 12.0f,
        .snr_decidb = 200,
    };
    CHECK(start_observer(&observer) == 0);
    CHECK(rls_awr2944p_observer_process(
        &observer, &detection, 1u, 100u, &output) == 0);

    CHECK(rls_awr2944p_observer_process(
        &observer, NULL, 0u, 200u, &output) == 0);
    CHECK(!output.fresh_detection);
    CHECK(output.measurement.target_id == 1u);
    CHECK(output.measurement.track_state == RLS_RADAR_TRACK_COASTING);
    CHECK(output.measurement.quality_flags == 0u);
    CHECK(output.measurement.range_mm == 0u);

    CHECK(rls_awr2944p_observer_process(
        &observer, NULL, 0u, 300u, &output) == 0);
    CHECK(output.measurement.track_state == RLS_RADAR_TRACK_COASTING);
    CHECK(rls_awr2944p_observer_process(
        &observer, NULL, 0u, 400u, &output) == 0);
    CHECK(output.measurement.target_id == 1u);
    CHECK(output.measurement.track_state == RLS_RADAR_TRACK_LOST);

    CHECK(rls_awr2944p_observer_process(
        &observer, &detection, 1u, 500u, &output) == 0);
    CHECK(output.measurement.target_id == 2u);
    CHECK(output.measurement.track_state == RLS_RADAR_TRACK_TENTATIVE);
    return 0;
}

static int test_filtering_and_association(void)
{
    rls_awr2944p_observer_t observer;
    rls_awr2944p_observer_output_t output;
    const rls_awr2944p_detection_t invalid[] = {
        {.x_m = 0.0f, .y_m = -10.0f, .snr_decidb = 300},
        {.x_m = 0.0f, .y_m = 10.0f, .snr_decidb = 20},
        {.x_m = 0.0f, .y_m = 400.0f, .snr_decidb = 300},
    };
    const rls_awr2944p_detection_t initial = {
        .x_m = 0.0f, .y_m = 50.0f, .snr_decidb = 160,
    };
    const rls_awr2944p_detection_t next[] = {
        {.x_m = 0.0f, .y_m = 51.0f, .snr_decidb = 140},
        {.x_m = 70.0f, .y_m = 70.0f, .snr_decidb = 300},
    };
    CHECK(start_observer(&observer) == 0);
    CHECK(rls_awr2944p_observer_process(
        &observer, invalid, 3u, 100u, &output) == 0);
    CHECK(output.measurement.track_state == RLS_RADAR_TRACK_NONE);
    CHECK(rls_awr2944p_observer_process(
        &observer, &initial, 1u, 200u, &output) == 0);
    CHECK(rls_awr2944p_observer_process(
        &observer, next, 2u, 300u, &output) == 0);
    CHECK(output.fresh_detection);
    CHECK(output.measurement.target_id == 1u);
    CHECK(output.measurement.range_mm >= 50649u);
    CHECK(output.measurement.range_mm <= 50651u);
    return 0;
}

static int test_can_contract_output(void)
{
    rls_awr2944p_observer_t observer;
    rls_awr2944p_observer_output_t output;
    rls_radar_link_frame_t frame;
    rls_radar_measurement_t measurement;
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE];
    const rls_awr2944p_detection_t detection = {
        .x_m = 1.0f,
        .y_m = 20.0f,
        .z_m = 2.0f,
        .radial_velocity_m_s = -4.5f,
        .snr_decidb = 180,
    };
    CHECK(start_observer(&observer) == 0);
    observer.config.profile_config_match = true;
    CHECK(rls_awr2944p_observer_process(
        &observer, &detection, 1u, UINT64_C(123456), &output) == 0);
    CHECK(rls_awr2944p_observer_build_can_frame(
        &observer, &output, wire) == RLS_RADAR_LINK_OK);
    memset(&frame, 0, sizeof(frame));
    memset(&measurement, 0, sizeof(measurement));
    CHECK(rls_radar_link_decode(
        wire, sizeof(wire), &frame) == RLS_RADAR_LINK_OK);
    CHECK(frame.type == RLS_RADAR_MSG_MEASUREMENT);
    CHECK(frame.sequence == 0u);
    CHECK(frame.timestamp_us == UINT64_C(123456));
    CHECK(frame.session_id == 0x10203040u);
    CHECK((frame.status_flags & RLS_RADAR_STATUS_DATA_VALID) != 0u);
    CHECK((frame.status_flags & RLS_RADAR_STATUS_CONFIG_MATCH) != 0u);
    CHECK(rls_radar_measurement_unpack(
        &frame, &measurement) == RLS_RADAR_LINK_OK);
    CHECK(measurement.target_id == 1u);

    CHECK(rls_awr2944p_observer_process(
        &observer, NULL, 0u, UINT64_C(124456), &output) == 0);
    CHECK(rls_awr2944p_observer_build_can_frame(
        &observer, &output, wire) == RLS_RADAR_LINK_OK);
    CHECK(rls_radar_link_decode(
        wire, sizeof(wire), &frame) == RLS_RADAR_LINK_OK);
    CHECK(frame.sequence == 1u);
    CHECK((frame.status_flags & RLS_RADAR_STATUS_DATA_VALID) == 0u);
    CHECK((frame.status_flags & RLS_RADAR_STATUS_DEGRADED) != 0u);
    return 0;
}

int main(void)
{
    CHECK(test_polar_measurement_and_confirmation() == 0);
    CHECK(test_coast_loss_and_reacquisition() == 0);
    CHECK(test_filtering_and_association() == 0);
    CHECK(test_can_contract_output() == 0);
    return 0;
}
