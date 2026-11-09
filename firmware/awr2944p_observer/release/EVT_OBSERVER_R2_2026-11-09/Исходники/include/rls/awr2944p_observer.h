#ifndef RLS_AWR2944P_OBSERVER_H
#define RLS_AWR2944P_OBSERVER_H

#include "rls/radar_link.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RLS_AWR2944P_OBSERVER_VERSION_MAJOR 0u
#define RLS_AWR2944P_OBSERVER_VERSION_MINOR 2u
#define RLS_AWR2944P_OBSERVER_VERSION_PATCH 0u

typedef struct {
    float x_m;
    float y_m;
    float z_m;
    float radial_velocity_m_s;
    int16_t snr_decidb;
    int16_t noise_decidb;
} rls_awr2944p_detection_t;

typedef struct {
    float min_range_m;
    float max_range_m;
    float max_abs_azimuth_deg;
    float max_abs_elevation_deg;
    float min_snr_db;
    float association_range_gate_m;
    float association_angle_gate_deg;
    float association_velocity_gate_m_s;
    float filter_alpha;
    uint8_t confirmation_hits;
    uint8_t maximum_coast_frames;
    bool profile_config_match;
    bool calibration_valid;
    bool uncertainty_valid;
    uint16_t range_sigma_mm;
    uint16_t velocity_sigma_mm_s;
    uint16_t azimuth_sigma_mdeg;
    uint16_t elevation_sigma_mdeg;
} rls_awr2944p_observer_config_t;

typedef struct {
    rls_radar_measurement_t measurement;
    uint64_t timestamp_us;
    uint16_t status_flags;
    bool fresh_detection;
} rls_awr2944p_observer_output_t;

typedef struct {
    rls_awr2944p_observer_config_t config;
    uint32_t session_id;
    uint32_t next_sequence;
    uint32_t next_target_id;
    uint32_t target_id;
    uint64_t frame_timestamp_us;
    float range_m;
    float radial_velocity_m_s;
    float azimuth_deg;
    float elevation_deg;
    int16_t snr_decidb;
    uint8_t hit_count;
    uint8_t miss_count;
    uint8_t track_state;
    bool active;
    bool frame_open;
    bool candidate_present;
    float candidate_score;
    float candidate_range_m;
    float candidate_radial_velocity_m_s;
    float candidate_azimuth_deg;
    float candidate_elevation_deg;
    int16_t candidate_snr_decidb;
} rls_awr2944p_observer_t;

void rls_awr2944p_observer_default_config(
    rls_awr2944p_observer_config_t *config
);

int rls_awr2944p_observer_init(
    rls_awr2944p_observer_t *observer,
    const rls_awr2944p_observer_config_t *config,
    uint32_t session_id,
    uint32_t initial_target_id
);

int rls_awr2944p_observer_begin_frame(
    rls_awr2944p_observer_t *observer,
    uint64_t timestamp_us
);

int rls_awr2944p_observer_consider_detection(
    rls_awr2944p_observer_t *observer,
    const rls_awr2944p_detection_t *detection
);

int rls_awr2944p_observer_end_frame(
    rls_awr2944p_observer_t *observer,
    rls_awr2944p_observer_output_t *output
);

int rls_awr2944p_observer_process(
    rls_awr2944p_observer_t *observer,
    const rls_awr2944p_detection_t *detections,
    size_t detection_count,
    uint64_t timestamp_us,
    rls_awr2944p_observer_output_t *output
);

int rls_awr2944p_observer_build_can_frame(
    rls_awr2944p_observer_t *observer,
    const rls_awr2944p_observer_output_t *output,
    uint8_t wire[RLS_RADAR_LINK_WIRE_SIZE]
);

#ifdef __cplusplus
}
#endif

#endif
