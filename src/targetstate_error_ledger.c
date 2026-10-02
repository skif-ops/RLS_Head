#include "rls/targetstate_error_ledger.h"

#include <math.h>
#include <stddef.h>
#include <string.h>

#define LEDGER_EPS 1.0e-12f

static bool valid_trace(float value)
{
    return isfinite(value) && value >= -LEDGER_EPS;
}

static float clamp_nonnegative(float value)
{
    if (value < 0.0f && value >= -LEDGER_EPS) {
        return 0.0f;
    }

    return value;
}

static void choose_if_larger(
    float candidate,
    TargetStateErrorSource source,
    float *best_value,
    TargetStateErrorSource *best_source)
{
    if (candidate > *best_value) {
        *best_value = candidate;
        *best_source = source;
    }
}

bool targetstate_build_error_ledger(
    const TargetStateSysErrResult *result,
    TargetStateErrorLedger *ledger)
{
    if (result == NULL || ledger == NULL) {
        return false;
    }

    TargetStateErrorLedger out;
    memset(&out, 0, sizeof(out));

    out.base_trace_m2 =
        sys_err_covariance_trace(
            &result->base_position_cov_m2);

    out.attitude_trace_m2 =
        sys_err_covariance_trace(
            &result->attitude_position_cov_m2);

    out.timestamp_trace_m2 =
        sys_err_covariance_trace(
            &result->timestamp_position_cov_m2);

    out.extrinsic_trace_m2 =
        sys_err_covariance_trace(
            &result->extrinsic_position_cov_m2);

    out.added_trace_m2 =
        sys_err_covariance_trace(
            &result->added_position_cov_m2);

    out.total_trace_m2 =
        sys_err_covariance_trace(
            &result->total_position_cov_m2);

    if (!valid_trace(out.base_trace_m2) ||
        !valid_trace(out.attitude_trace_m2) ||
        !valid_trace(out.timestamp_trace_m2) ||
        !valid_trace(out.extrinsic_trace_m2) ||
        !valid_trace(out.added_trace_m2) ||
        !valid_trace(out.total_trace_m2)) {
        return false;
    }

    out.base_trace_m2 =
        clamp_nonnegative(out.base_trace_m2);

    out.attitude_trace_m2 =
        clamp_nonnegative(out.attitude_trace_m2);

    out.timestamp_trace_m2 =
        clamp_nonnegative(out.timestamp_trace_m2);

    out.extrinsic_trace_m2 =
        clamp_nonnegative(out.extrinsic_trace_m2);

    out.added_trace_m2 =
        clamp_nonnegative(out.added_trace_m2);

    out.total_trace_m2 =
        clamp_nonnegative(out.total_trace_m2);

    const float component_added =
        out.attitude_trace_m2 +
        out.timestamp_trace_m2 +
        out.extrinsic_trace_m2;

    const float reconstructed_total =
        out.base_trace_m2 +
        component_added;

    const float tolerance =
        1.0e-5f *
        fmaxf(1.0f, out.total_trace_m2);

    if (fabsf(component_added - out.added_trace_m2) > tolerance ||
        fabsf(reconstructed_total - out.total_trace_m2) > tolerance) {
        return false;
    }

    if (out.total_trace_m2 > LEDGER_EPS) {
        out.base_fraction_total =
            out.base_trace_m2 /
            out.total_trace_m2;

        out.attitude_fraction_total =
            out.attitude_trace_m2 /
            out.total_trace_m2;

        out.timestamp_fraction_total =
            out.timestamp_trace_m2 /
            out.total_trace_m2;

        out.extrinsic_fraction_total =
            out.extrinsic_trace_m2 /
            out.total_trace_m2;
    }

    float best_overall =
        out.base_trace_m2;

    out.dominant_overall_source =
        TS_ERROR_SOURCE_BASE_TRACK;

    choose_if_larger(
        out.attitude_trace_m2,
        TS_ERROR_SOURCE_HOST_ATTITUDE,
        &best_overall,
        &out.dominant_overall_source);

    choose_if_larger(
        out.timestamp_trace_m2,
        TS_ERROR_SOURCE_TIMESTAMP,
        &best_overall,
        &out.dominant_overall_source);

    choose_if_larger(
        out.extrinsic_trace_m2,
        TS_ERROR_SOURCE_EXTRINSIC,
        &best_overall,
        &out.dominant_overall_source);

    if (out.total_trace_m2 > LEDGER_EPS) {
        out.dominant_overall_fraction =
            best_overall /
            out.total_trace_m2;
    } else {
        out.dominant_overall_source =
            TS_ERROR_SOURCE_NONE;
    }

    float best_added =
        out.attitude_trace_m2;

    out.dominant_added_source =
        TS_ERROR_SOURCE_HOST_ATTITUDE;

    choose_if_larger(
        out.timestamp_trace_m2,
        TS_ERROR_SOURCE_TIMESTAMP,
        &best_added,
        &out.dominant_added_source);

    choose_if_larger(
        out.extrinsic_trace_m2,
        TS_ERROR_SOURCE_EXTRINSIC,
        &best_added,
        &out.dominant_added_source);

    if (out.added_trace_m2 > LEDGER_EPS) {
        out.dominant_added_fraction =
            best_added /
            out.added_trace_m2;
    } else {
        out.dominant_added_source =
            TS_ERROR_SOURCE_NONE;
    }

    *ledger = out;
    return true;
}

const char *targetstate_error_source_name(
    TargetStateErrorSource source)
{
    switch (source) {
    case TS_ERROR_SOURCE_BASE_TRACK:
        return "BASE_TRACK";

    case TS_ERROR_SOURCE_HOST_ATTITUDE:
        return "HOST_ATTITUDE";

    case TS_ERROR_SOURCE_TIMESTAMP:
        return "TIMESTAMP";

    case TS_ERROR_SOURCE_EXTRINSIC:
        return "EXTRINSIC";

    case TS_ERROR_SOURCE_NONE:
    default:
        return "NONE";
    }
}
