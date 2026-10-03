#include "rls/hil_r2_evidence.h"

#include <float.h>
#include <math.h>
#include <stddef.h>
#include <string.h>

void hil_r2_residual_stats_reset(
    HilR2ResidualStats *stats)
{
    if (stats == NULL) {
        return;
    }

    memset(stats, 0, sizeof(*stats));
    stats->min_us = FLT_MAX;
    stats->max_us = -FLT_MAX;
}

bool hil_r2_residual_stats_push(
    HilR2ResidualStats *stats,
    float residual_us)
{
    if (stats == NULL || !isfinite(residual_us)) {
        return false;
    }

    if (stats->count == 0u) {
        stats->count = 1u;
        stats->mean_us = (double)residual_us;
        stats->m2_us2 = 0.0;
        stats->min_us = residual_us;
        stats->max_us = residual_us;
        stats->max_abs_us = fabsf(residual_us);
        return true;
    }

    const uint32_t new_count = stats->count + 1u;
    const double delta =
        (double)residual_us - stats->mean_us;

    stats->mean_us += delta / (double)new_count;

    const double delta2 =
        (double)residual_us - stats->mean_us;

    stats->m2_us2 += delta * delta2;
    stats->count = new_count;

    if (residual_us < stats->min_us) {
        stats->min_us = residual_us;
    }

    if (residual_us > stats->max_us) {
        stats->max_us = residual_us;
    }

    const float abs_value = fabsf(residual_us);

    if (abs_value > stats->max_abs_us) {
        stats->max_abs_us = abs_value;
    }

    return isfinite(stats->mean_us) &&
           isfinite(stats->m2_us2);
}

float hil_r2_residual_stats_rms(
    const HilR2ResidualStats *stats)
{
    if (stats == NULL || stats->count == 0u) {
        return NAN;
    }

    const double mean_sq =
        stats->m2_us2 / (double)stats->count +
        stats->mean_us * stats->mean_us;

    if (!isfinite(mean_sq) || mean_sq < 0.0) {
        return NAN;
    }

    return (float)sqrt(mean_sq);
}

float hil_r2_residual_stats_stddev(
    const HilR2ResidualStats *stats)
{
    if (stats == NULL || stats->count < 2u) {
        return NAN;
    }

    const double variance =
        stats->m2_us2 / (double)(stats->count - 1u);

    if (!isfinite(variance) || variance < 0.0) {
        return NAN;
    }

    return (float)sqrt(variance);
}

void hil_r2_evidence_reset(
    HilR2Evidence *evidence)
{
    if (evidence == NULL) {
        return;
    }

    memset(evidence, 0, sizeof(*evidence));

    hil_r2_residual_stats_reset(
        &evidence->radar_imu_us);

    hil_r2_residual_stats_reset(
        &evidence->pps_us);
}

bool hil_r2_evidence_record_radar_imu(
    HilR2Evidence *evidence,
    float residual_us)
{
    if (evidence == NULL) {
        return false;
    }

    ++evidence->radar_ref_events;
    ++evidence->imu_drdy_events;

    return hil_r2_residual_stats_push(
        &evidence->radar_imu_us,
        residual_us);
}

bool hil_r2_evidence_record_pps(
    HilR2Evidence *evidence,
    float residual_us)
{
    if (evidence == NULL) {
        return false;
    }

    ++evidence->pps_events;

    return hil_r2_residual_stats_push(
        &evidence->pps_us,
        residual_us);
}

bool hil_r2_evidence_update_holdover(
    HilR2Evidence *evidence,
    float error_us)
{
    if (evidence == NULL || !isfinite(error_us)) {
        return false;
    }

    const float abs_error = fabsf(error_us);

    if (abs_error > evidence->holdover_max_abs_us) {
        evidence->holdover_max_abs_us = abs_error;
    }

    return true;
}

static uint32_t total_missed_events(
    const HilR2Evidence *evidence)
{
    return
        evidence->radar_ref_missed +
        evidence->imu_drdy_missed +
        evidence->pps_missed;
}

HilR2EvidenceGateStatus hil_r2_evidence_evaluate(
    const HilR2Evidence *evidence,
    const HilR2EvidenceGateConfig *config)
{
    if (evidence == NULL || config == NULL) {
        return HIL_R2_EVIDENCE_INSUFFICIENT;
    }

    if (evidence->radar_imu_us.count <
            config->min_radar_imu_samples ||
        evidence->pps_us.count <
            config->min_pps_samples) {
        return HIL_R2_EVIDENCE_INSUFFICIENT;
    }

    const float radar_imu_rms =
        hil_r2_residual_stats_rms(
            &evidence->radar_imu_us);

    if (!isfinite(radar_imu_rms) ||
        evidence->radar_imu_us.max_abs_us >
            config->radar_imu_max_abs_us ||
        radar_imu_rms >
            config->radar_imu_rms_us) {
        return HIL_R2_EVIDENCE_RADAR_IMU_FAIL;
    }

    const float pps_rms =
        hil_r2_residual_stats_rms(
            &evidence->pps_us);

    if (!isfinite(pps_rms) ||
        evidence->pps_us.max_abs_us >
            config->pps_max_abs_us ||
        pps_rms >
            config->pps_rms_us) {
        return HIL_R2_EVIDENCE_PPS_FAIL;
    }

    if (evidence->holdover_max_abs_us >
        config->holdover_max_abs_us) {
        return HIL_R2_EVIDENCE_HOLDOVER_FAIL;
    }

    if (total_missed_events(evidence) >
        config->max_missed_events) {
        return HIL_R2_EVIDENCE_CAPTURE_FAIL;
    }

    if (evidence->monotonic_failures >
        config->max_monotonic_failures) {
        return HIL_R2_EVIDENCE_TIME_FAIL;
    }

    return HIL_R2_EVIDENCE_PASS;
}
