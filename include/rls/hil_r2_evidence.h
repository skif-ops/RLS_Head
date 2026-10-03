#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint32_t count;
    double mean_us;
    double m2_us2;
    float min_us;
    float max_us;
    float max_abs_us;
} HilR2ResidualStats;

typedef struct {
    HilR2ResidualStats radar_imu_us;
    HilR2ResidualStats pps_us;

    uint32_t radar_ref_events;
    uint32_t imu_drdy_events;
    uint32_t pps_events;

    uint32_t radar_ref_missed;
    uint32_t imu_drdy_missed;
    uint32_t pps_missed;

    uint32_t monotonic_failures;

    float holdover_max_abs_us;
} HilR2Evidence;

typedef struct {
    uint32_t min_radar_imu_samples;
    uint32_t min_pps_samples;

    float radar_imu_max_abs_us;
    float radar_imu_rms_us;

    float pps_max_abs_us;
    float pps_rms_us;

    float holdover_max_abs_us;

    uint32_t max_missed_events;
    uint32_t max_monotonic_failures;
} HilR2EvidenceGateConfig;

typedef enum {
    HIL_R2_EVIDENCE_PASS = 0,
    HIL_R2_EVIDENCE_INSUFFICIENT,
    HIL_R2_EVIDENCE_RADAR_IMU_FAIL,
    HIL_R2_EVIDENCE_PPS_FAIL,
    HIL_R2_EVIDENCE_HOLDOVER_FAIL,
    HIL_R2_EVIDENCE_CAPTURE_FAIL,
    HIL_R2_EVIDENCE_TIME_FAIL
} HilR2EvidenceGateStatus;

void hil_r2_residual_stats_reset(
    HilR2ResidualStats *stats);

bool hil_r2_residual_stats_push(
    HilR2ResidualStats *stats,
    float residual_us);

float hil_r2_residual_stats_rms(
    const HilR2ResidualStats *stats);

float hil_r2_residual_stats_stddev(
    const HilR2ResidualStats *stats);

void hil_r2_evidence_reset(
    HilR2Evidence *evidence);

bool hil_r2_evidence_record_radar_imu(
    HilR2Evidence *evidence,
    float residual_us);

bool hil_r2_evidence_record_pps(
    HilR2Evidence *evidence,
    float residual_us);

bool hil_r2_evidence_update_holdover(
    HilR2Evidence *evidence,
    float error_us);

HilR2EvidenceGateStatus hil_r2_evidence_evaluate(
    const HilR2Evidence *evidence,
    const HilR2EvidenceGateConfig *config);

#ifdef __cplusplus
}
#endif
