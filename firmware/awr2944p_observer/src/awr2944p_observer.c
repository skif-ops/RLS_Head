#include "rls/awr2944p_observer.h"

#include <limits.h>
#include <math.h>
#include <string.h>

#define RLS_RAD_TO_DEG 57.2957795130823208768f

static bool config_is_valid(const rls_awr2944p_observer_config_t *config)
{
    if (config == NULL
        || !isfinite(config->min_range_m)
        || !isfinite(config->max_range_m)
        || !isfinite(config->max_abs_azimuth_deg)
        || !isfinite(config->max_abs_elevation_deg)
        || !isfinite(config->min_snr_db)
        || !isfinite(config->association_range_gate_m)
        || !isfinite(config->association_angle_gate_deg)
        || !isfinite(config->association_velocity_gate_m_s)
        || !isfinite(config->filter_alpha)) {
        return false;
    }
    if (config->min_range_m < 0.0f
        || config->max_range_m <= config->min_range_m
        || config->max_abs_azimuth_deg <= 0.0f
        || config->max_abs_elevation_deg <= 0.0f
        || config->association_range_gate_m <= 0.0f
        || config->association_angle_gate_deg <= 0.0f
        || config->association_velocity_gate_m_s <= 0.0f
        || config->filter_alpha <= 0.0f
        || config->filter_alpha > 1.0f
        || config->confirmation_hits == 0u) {
        return false;
    }
    if (config->uncertainty_valid
        && (config->range_sigma_mm == 0u
            || config->velocity_sigma_mm_s == 0u
            || config->azimuth_sigma_mdeg == 0u
            || config->elevation_sigma_mdeg == 0u)) {
        return false;
    }
    return true;
}

static uint32_t next_nonzero_u32(uint32_t value)
{
    return value == UINT32_MAX ? 1u : value + 1u;
}

static uint32_t to_u32_scaled(float value, float scale)
{
    const double scaled = (double)value * (double)scale;
    if (scaled <= 0.0) {
        return 0u;
    }
    if (scaled >= (double)UINT32_MAX) {
        return UINT32_MAX;
    }
    return (uint32_t)lround(scaled);
}

static int32_t to_i32_scaled(float value, float scale)
{
    const double scaled = (double)value * (double)scale;
    if (scaled <= (double)INT32_MIN) {
        return INT32_MIN;
    }
    if (scaled >= (double)INT32_MAX) {
        return INT32_MAX;
    }
    return (int32_t)lround(scaled);
}

static int16_t decidb_to_cdb(int16_t value)
{
    const int32_t scaled = (int32_t)value * 10;
    if (scaled < INT16_MIN) {
        return INT16_MIN;
    }
    if (scaled > INT16_MAX) {
        return INT16_MAX;
    }
    return (int16_t)scaled;
}

static void make_empty_output(
    const rls_awr2944p_observer_t *observer,
    rls_awr2944p_observer_output_t *output)
{
    memset(output, 0, sizeof(*output));
    output->timestamp_us = observer->frame_timestamp_us;
    if (observer->config.profile_config_match) {
        output->status_flags |= RLS_RADAR_STATUS_CONFIG_MATCH;
    }
    if (observer->frame_timestamp_us != 0u) {
        output->status_flags |= RLS_RADAR_STATUS_TIME_VALID;
    }
    if (observer->config.calibration_valid) {
        output->status_flags |= RLS_RADAR_STATUS_CALIBRATION_VALID;
    }
}

static void fill_fresh_output(
    const rls_awr2944p_observer_t *observer,
    rls_awr2944p_observer_output_t *output)
{
    make_empty_output(observer, output);
    output->fresh_detection = true;
    output->status_flags |= RLS_RADAR_STATUS_DATA_VALID;
    output->measurement.target_id = observer->target_id;
    output->measurement.range_mm = to_u32_scaled(observer->range_m, 1000.0f);
    output->measurement.radial_velocity_mm_s =
        to_i32_scaled(observer->radial_velocity_m_s, 1000.0f);
    output->measurement.azimuth_mdeg =
        to_i32_scaled(observer->azimuth_deg, 1000.0f);
    output->measurement.elevation_mdeg =
        to_i32_scaled(observer->elevation_deg, 1000.0f);
    output->measurement.snr_cdb = decidb_to_cdb(observer->snr_decidb);
    output->measurement.track_state = observer->track_state;
    output->measurement.quality_flags =
        RLS_RADAR_QUALITY_RANGE_VALID
        | RLS_RADAR_QUALITY_VELOCITY_VALID
        | RLS_RADAR_QUALITY_AZIMUTH_VALID
        | RLS_RADAR_QUALITY_ELEVATION_VALID
        | RLS_RADAR_QUALITY_SNR_VALID;
    if (observer->track_state == RLS_RADAR_TRACK_CONFIRMED) {
        output->measurement.quality_flags |= RLS_RADAR_QUALITY_TRACK_CONFIRMED;
    }
    if (observer->config.calibration_valid) {
        output->measurement.quality_flags |= RLS_RADAR_QUALITY_CALIBRATION_VALID;
    }
    if (observer->config.uncertainty_valid) {
        output->measurement.range_sigma_mm = observer->config.range_sigma_mm;
        output->measurement.velocity_sigma_mm_s =
            observer->config.velocity_sigma_mm_s;
        output->measurement.azimuth_sigma_mdeg =
            observer->config.azimuth_sigma_mdeg;
        output->measurement.elevation_sigma_mdeg =
            observer->config.elevation_sigma_mdeg;
        output->measurement.quality_flags |= RLS_RADAR_QUALITY_UNCERTAINTY_VALID;
    }
}

static void fill_nonfresh_track_output(
    const rls_awr2944p_observer_t *observer,
    uint32_t target_id,
    uint8_t track_state,
    rls_awr2944p_observer_output_t *output)
{
    make_empty_output(observer, output);
    output->status_flags |= RLS_RADAR_STATUS_DEGRADED;
    output->measurement.target_id = target_id;
    output->measurement.track_state = track_state;
}

void rls_awr2944p_observer_default_config(
    rls_awr2944p_observer_config_t *config)
{
    if (config == NULL) {
        return;
    }
    memset(config, 0, sizeof(*config));
    config->min_range_m = 0.5f;
    config->max_range_m = 350.0f;
    config->max_abs_azimuth_deg = 60.0f;
    config->max_abs_elevation_deg = 22.0f;
    config->min_snr_db = 12.0f;
    config->association_range_gate_m = 20.0f;
    config->association_angle_gate_deg = 8.0f;
    config->association_velocity_gate_m_s = 20.0f;
    config->filter_alpha = 0.65f;
    config->confirmation_hits = 3u;
    config->maximum_coast_frames = 2u;
}

int rls_awr2944p_observer_init(
    rls_awr2944p_observer_t *observer,
    const rls_awr2944p_observer_config_t *config,
    uint32_t session_id,
    uint32_t initial_target_id)
{
    if (observer == NULL
        || !config_is_valid(config)
        || session_id == 0u
        || initial_target_id == 0u) {
        return -1;
    }
    memset(observer, 0, sizeof(*observer));
    observer->config = *config;
    observer->session_id = session_id;
    observer->next_target_id = initial_target_id;
    return 0;
}

int rls_awr2944p_observer_begin_frame(
    rls_awr2944p_observer_t *observer,
    uint64_t timestamp_us)
{
    if (observer == NULL || observer->frame_open) {
        return -1;
    }
    observer->frame_timestamp_us = timestamp_us;
    observer->candidate_present = false;
    observer->candidate_score = INFINITY;
    observer->frame_open = true;
    return 0;
}

int rls_awr2944p_observer_consider_detection(
    rls_awr2944p_observer_t *observer,
    const rls_awr2944p_detection_t *detection)
{
    if (observer == NULL || detection == NULL || !observer->frame_open) {
        return -1;
    }
    if (!isfinite(detection->x_m)
        || !isfinite(detection->y_m)
        || !isfinite(detection->z_m)
        || !isfinite(detection->radial_velocity_m_s)) {
        return 0;
    }

    const float horizontal_m = hypotf(detection->x_m, detection->y_m);
    const float range_m = hypotf(horizontal_m, detection->z_m);
    const float azimuth_deg = atan2f(detection->x_m, detection->y_m)
        * RLS_RAD_TO_DEG;
    const float elevation_deg = atan2f(detection->z_m, horizontal_m)
        * RLS_RAD_TO_DEG;
    const float snr_db = (float)detection->snr_decidb * 0.1f;

    if (detection->y_m <= 0.0f
        || range_m < observer->config.min_range_m
        || range_m > observer->config.max_range_m
        || fabsf(azimuth_deg) > observer->config.max_abs_azimuth_deg
        || fabsf(elevation_deg) > observer->config.max_abs_elevation_deg
        || snr_db < observer->config.min_snr_db) {
        return 0;
    }

    float score;
    if (observer->active) {
        const float range_term = fabsf(range_m - observer->range_m)
            / observer->config.association_range_gate_m;
        const float azimuth_term = fabsf(azimuth_deg - observer->azimuth_deg)
            / observer->config.association_angle_gate_deg;
        const float elevation_term = fabsf(elevation_deg - observer->elevation_deg)
            / observer->config.association_angle_gate_deg;
        const float velocity_term = fabsf(
            detection->radial_velocity_m_s - observer->radial_velocity_m_s)
            / observer->config.association_velocity_gate_m_s;
        if (range_term > 1.0f
            || azimuth_term > 1.0f
            || elevation_term > 1.0f
            || velocity_term > 1.0f) {
            return 0;
        }
        score = range_term * range_term
            + azimuth_term * azimuth_term
            + elevation_term * elevation_term
            + velocity_term * velocity_term
            - 0.001f * snr_db;
    } else {
        score = -snr_db + 0.001f * range_m;
    }

    if (!observer->candidate_present || score < observer->candidate_score) {
        observer->candidate_present = true;
        observer->candidate_score = score;
        observer->candidate_range_m = range_m;
        observer->candidate_radial_velocity_m_s = detection->radial_velocity_m_s;
        observer->candidate_azimuth_deg = azimuth_deg;
        observer->candidate_elevation_deg = elevation_deg;
        observer->candidate_snr_decidb = detection->snr_decidb;
    }
    return 0;
}

int rls_awr2944p_observer_end_frame(
    rls_awr2944p_observer_t *observer,
    rls_awr2944p_observer_output_t *output)
{
    if (observer == NULL || output == NULL || !observer->frame_open) {
        return -1;
    }
    observer->frame_open = false;

    if (observer->candidate_present) {
        if (!observer->active) {
            observer->active = true;
            observer->target_id = observer->next_target_id;
            observer->next_target_id = next_nonzero_u32(observer->next_target_id);
            observer->range_m = observer->candidate_range_m;
            observer->radial_velocity_m_s =
                observer->candidate_radial_velocity_m_s;
            observer->azimuth_deg = observer->candidate_azimuth_deg;
            observer->elevation_deg = observer->candidate_elevation_deg;
            observer->hit_count = 1u;
        } else {
            const float alpha = observer->config.filter_alpha;
            observer->range_m += alpha
                * (observer->candidate_range_m - observer->range_m);
            observer->radial_velocity_m_s += alpha
                * (observer->candidate_radial_velocity_m_s
                    - observer->radial_velocity_m_s);
            observer->azimuth_deg += alpha
                * (observer->candidate_azimuth_deg - observer->azimuth_deg);
            observer->elevation_deg += alpha
                * (observer->candidate_elevation_deg - observer->elevation_deg);
            if (observer->hit_count < UINT8_MAX) {
                observer->hit_count++;
            }
        }
        observer->snr_decidb = observer->candidate_snr_decidb;
        observer->miss_count = 0u;
        observer->track_state = observer->hit_count
                >= observer->config.confirmation_hits
            ? RLS_RADAR_TRACK_CONFIRMED
            : RLS_RADAR_TRACK_TENTATIVE;
        fill_fresh_output(observer, output);
        return 0;
    }

    if (!observer->active) {
        make_empty_output(observer, output);
        return 0;
    }

    if (observer->miss_count < UINT8_MAX) {
        observer->miss_count++;
    }
    if (observer->miss_count <= observer->config.maximum_coast_frames) {
        observer->track_state = RLS_RADAR_TRACK_COASTING;
        fill_nonfresh_track_output(
            observer,
            observer->target_id,
            RLS_RADAR_TRACK_COASTING,
            output);
        return 0;
    }

    const uint32_t lost_target_id = observer->target_id;
    observer->active = false;
    observer->target_id = 0u;
    observer->hit_count = 0u;
    observer->miss_count = 0u;
    observer->track_state = RLS_RADAR_TRACK_NONE;
    fill_nonfresh_track_output(
        observer,
        lost_target_id,
        RLS_RADAR_TRACK_LOST,
        output);
    return 0;
}

int rls_awr2944p_observer_process(
    rls_awr2944p_observer_t *observer,
    const rls_awr2944p_detection_t *detections,
    size_t detection_count,
    uint64_t timestamp_us,
    rls_awr2944p_observer_output_t *output)
{
    if (observer == NULL
        || output == NULL
        || (detections == NULL && detection_count != 0u)) {
        return -1;
    }
    if (rls_awr2944p_observer_begin_frame(observer, timestamp_us) != 0) {
        return -1;
    }
    for (size_t i = 0u; i < detection_count; ++i) {
        if (rls_awr2944p_observer_consider_detection(
                observer, &detections[i]) != 0) {
            observer->frame_open = false;
            return -1;
        }
    }
    return rls_awr2944p_observer_end_frame(observer, output);
}

int rls_awr2944p_observer_build_can_frame(
    rls_awr2944p_observer_t *observer,
    const rls_awr2944p_observer_output_t *output,
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE])
{
    if (observer == NULL || output == NULL || wire == NULL) {
        return RLS_RADAR_LINK_ERROR_ARGUMENT;
    }
    rls_radar_link_frame_t frame;
    memset(&frame, 0, sizeof(frame));
    frame.version = RLS_RADAR_LINK_VERSION;
    frame.status_flags = output->status_flags;
    frame.sequence = observer->next_sequence++;
    frame.timestamp_us = output->timestamp_us;
    frame.session_id = observer->session_id;
    int result = rls_radar_measurement_pack(&output->measurement, &frame);
    if (result != RLS_RADAR_LINK_OK) {
        return result;
    }
    return rls_radar_link_encode(&frame, wire, RLS_RADAR_LINK_WIRE_SIZE);
}
